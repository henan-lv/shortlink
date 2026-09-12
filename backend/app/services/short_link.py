"""短链业务服务(PRD 第 5 章 F1.1 ~ F1.4 + F3)。

提供短链生成、跳转、查询、统计、删除、启停等业务方法。
"""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..middleware.error import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from ..models import AccessRule, AccessRuleSource, ClickLog, ShortLink, ShortLinkStatus
from ..utils.hashing import url_hash
from . import access_control
from .security import SecurityChecker
from .short_code import encode_id
from . import password as password_service


# ---------- 长链校验 ----------

def validate_long_url(url: str, max_length: int = 2048) -> None:
    if not isinstance(url, str) or not url:
        raise BadRequestError("链接不能为空")
    if len(url) > max_length:
        raise BadRequestError(f"链接长度超过 {max_length}")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BadRequestError("链接必须以 http:// 或 https:// 开头")
    if not parsed.netloc:
        raise BadRequestError("链接格式不正确")


# ---------- 安全检查器 ----------

def build_security_checker() -> SecurityChecker:
    """根据当前应用配置构造 SecurityChecker。"""
    cfg = current_app.config
    enabled = cfg.get("SECURITY_ENABLED", True)
    fail_open = cfg.get("SECURITY_FAIL_OPEN", False)
    check_create = cfg.get("SECURITY_CHECK_ON_CREATE", True)
    if not check_create:
        # 关掉生成时校验,临时禁用(跳转校验独立)
        enabled = False
    rules = _load_blacklist_rules()
    return SecurityChecker(rules=rules, enabled=enabled, fail_open=fail_open)


def _load_blacklist_rules():
    """从 DB 加载黑名单规则。失败时返回空(降级策略由 fail_open 决定)。"""
    try:
        from ..models import Blacklist
        return [r.to_rule() for r in Blacklist.query.filter_by(enabled=True).all()]
    except Exception:
        return []


# ---------- 短链生成 ----------

def create(
    long_url: str,
    *,
    password: Optional[str] = None,
    expire_at: Optional[datetime] = None,
    effective_at: Optional[datetime] = None,
    click_limit: Optional[int] = None,
    user_id: Optional[int] = None,
    domain: Optional[str] = None,
    channel: Optional[str] = None,
    advanced: Optional[dict] = None,
) -> ShortLink:
    """生成短链(PRD F1.1)。

    advanced:生成页「高级设置」,结构见 services/access_control.parse_advanced。
              传入时会覆盖该短链此前由高级设置产生的风控规则(幂等)。
    """
    cfg = current_app.config
    validate_long_url(long_url, cfg["LONG_URL_MAX_LENGTH"])

    checker = build_security_checker()
    if checker.is_malicious(long_url):
        raise BadRequestError("链接被拦截")

    if password:
        password_service.validate_password_length(
            password,
            cfg["PASSWORD_MIN_LENGTH"],
            cfg["PASSWORD_MAX_LENGTH"],
        )

    if expire_at is not None:
        # 统一转 naive UTC,兼容 MySQL DateTime(无 tz)字段
        if expire_at.tzinfo is not None:
            expire_at = expire_at.astimezone(timezone.utc).replace(tzinfo=None)
        if expire_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise BadRequestError("过期时间不能早于当前时间")

    if effective_at is not None:
        if effective_at.tzinfo is not None:
            effective_at = effective_at.astimezone(timezone.utc).replace(tzinfo=None)
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        if effective_at < now_naive:
            raise BadRequestError("生效时间不能早于当前时间")

    # 规范化:None / 全空格 一律看作空。这与旧行 domain/channel 都为 NULL 的情况叠加上新哈希算法后仍可互找
    norm_domain = (domain or "").strip() or None
    norm_channel = (channel or "").strip() or None

    h = url_hash(long_url, norm_domain or "", norm_channel or "")

    # 同链 + 同域名 + 同渠道 查重(Plan D: 只有三者都同才返回同码)
    existing = (
        ShortLink.query.filter_by(
            url_hash=h,
            domain=norm_domain,
            channel=norm_channel,
            is_deleted=False,
        ).first()
    )
    if existing:
        # 同链同码:高级设置按"覆盖"语义同步,保证幂等(重复提交不会堆规则)
        if advanced is not None:
            _sync_advanced_rules(existing, advanced)
        return existing

    pwd_hash = password_service.hash_password(password) if password else None

    sl = ShortLink(
        user_id=user_id,
        short_code="000000",  # 临时占位,commit 后用真实 id 重算
        long_url=long_url,
        url_hash=h,
        domain=norm_domain,
        channel=norm_channel,
        password_hash=pwd_hash,
        effective_at=effective_at,
        expire_at=expire_at,
        click_limit=click_limit,
    )
    db.session.add(sl)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        # 并发同链,回查
        cached = ShortLink.query.filter_by(
            url_hash=h, domain=norm_domain, channel=norm_channel, is_deleted=False
        ).first()
        if cached:
            return cached
        raise

    sl.short_code = encode_id(
        sl.id,
        cfg["SHORT_CODE_AFFINE_MULTIPLIER"],
        cfg["SHORT_CODE_AFFINE_OFFSET"],
        cfg["SHORT_CODE_MIN_LENGTH"],
    )

    # 高级设置 → 风控规则(此时 short_code 已定,可安全关联)
    if advanced is not None:
        access_control.sync_advanced_rules(sl, advanced, sl.user_id)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        cached = ShortLink.query.filter_by(
            url_hash=h, domain=norm_domain, channel=norm_channel, is_deleted=False
        ).first()
        if cached:
            return cached
        raise

    # 规则已落库,递增缓存版本号让新规则立即生效
    if advanced is not None:
        access_control.bump_version(sl.user_id)

    return sl


def _sync_advanced_rules(sl: ShortLink, advanced: dict) -> None:
    """对已存在的短链同步高级设置规则,并让缓存立即失效。"""
    access_control.sync_advanced_rules(sl, advanced, sl.user_id)
    db.session.commit()
    access_control.bump_version(sl.user_id)


# ---------- 查询 ----------

def get_by_code(short_code: str) -> Optional[ShortLink]:
    """按短码查询(包含软删记录,用于后台操作)。"""
    return ShortLink.query.filter_by(short_code=short_code).first()


def get_active_by_code(short_code: str) -> Optional[ShortLink]:
    """按短码查询未软删的记录。"""
    return ShortLink.query.filter_by(
        short_code=short_code, is_deleted=False
    ).first()


# ---------- 跳转前置检查 ----------

class RedirectOutcome:
    OK = "ok"
    MALICIOUS = "malicious"
    GONE = "gone"           # 过期/软删/停用/超限
    UNAUTHORIZED = "unauthorized"  # 需密码
    NOT_FOUND = "not_found"
    NOT_EFFECTIVE = "not_effective"   # 未到生效时间
    SERVICE_UNAVAILABLE = "service_unavailable"  # 全局熔断
    FORBIDDEN_WHITELIST = "forbidden_whitelist"  # IP 不在白名单
    FORBIDDEN_BOT = "forbidden_bot"  # UA 命中黑名单


def redirect_pre_check(sl: ShortLink, cookies=None) -> tuple[str, int]:
    """跳转前置检查,返回 (outcome, http_status)。

    状态码映射(PRD 第 11 章):
      - 短码不存在 / 已软删 → 404 NOT_FOUND(对用户透明,不暴露是否曾存在)
      - 已过期 / 已停用 / 超限 → 410 GONE
      - 恶意 → 403 FORBIDDEN
      - 需密码 → 401 UNAUTHORIZED

    cookies: dict-like(默认 None),用于校验 pw_<short_code> 凭证。
             密码链若携带合法凭证(签名正确、未过期)则放行,否则 401。
    """
    if sl is None or sl.is_deleted:
        return RedirectOutcome.NOT_FOUND, 404
    if sl.status == ShortLinkStatus.MALICIOUS:
        return RedirectOutcome.MALICIOUS, 403
    if sl.status == ShortLinkStatus.DISABLED:
        return RedirectOutcome.GONE, 410
    if sl.is_expired():
        return RedirectOutcome.GONE, 410
    if sl.is_not_effective():
        return RedirectOutcome.NOT_EFFECTIVE, 403
    if sl.click_limit and sl.visit_count >= sl.click_limit:
        return RedirectOutcome.GONE, 410
    if sl.password_hash:
        if cookies and _has_valid_pw_cookie(sl.short_code, cookies):
            return RedirectOutcome.OK, 302
        return RedirectOutcome.UNAUTHORIZED, 401
    return RedirectOutcome.OK, 302


def _has_valid_pw_cookie(short_code: str, cookies) -> bool:
    """校验 pw_<short_code> cookie 是否签名合法且未过期。"""
    if not cookies:
        return False
    token = cookies.get(f"pw_{short_code}")
    if not token:
        return False
    secret = current_app.config["SECRET_KEY"]
    return password_service.verify_token(token, short_code, secret)


# ---------- 点击记录 ----------

def record_click(
    sl: ShortLink,
    ip: str,
    user_agent: Optional[str] = None,
    referer: Optional[str] = None,
) -> None:
    """PV 自增 + 写点击日志(同步,PRD Q14 暂不同步异步)。"""
    sl.visit_count = (sl.visit_count or 0) + 1
    sl.last_visit_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add(ClickLog(
        short_code=sl.short_code, ip=ip,
        user_agent=user_agent, referer=referer,
    ))
    db.session.commit()


# ---------- 统计 ----------

def get_uv(sl: ShortLink) -> int:
    """UV 按 IP 去重(同一短码 + IP 计 1)。"""
    return (
        db.session.query(func.count(func.distinct(ClickLog.ip)))
        .filter(ClickLog.short_code == sl.short_code)
        .scalar()
        or 0
    )


# ---------- 修改 ----------

def soft_delete(sl: ShortLink) -> None:
    """软删除(PRD Q2 短码不复用)。

    同时把 url_hash 替换为 `del-{id}` 占位符,从全局唯一索引里挪走,
    避免后续再用同一长链生成时报 Duplicate entry 500。
    活跃记录的 dedup 查询过滤了 is_deleted=False,占位符不影响去重逻辑。
    替换而不是拼接是因为 url_hash 是 String(64),拼接容易超长。

    原始哈希未被销毁:它可由 (long_url, domain, channel) 精确重算,
    因此该操作可逆,见 restore()。幂等,重复调用无副作用。
    """
    if sl.is_deleted:
        return
    sl.is_deleted = True
    sl.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    sl.url_hash = f"del-{sl.id}"
    db.session.commit()


def restore(sl: ShortLink) -> ShortLink:
    """恢复软删短链(误删撤销),撤销 soft_delete 的全部副作用。

    soft_delete 把 url_hash 换成了 `del-{id}` 占位符,这里用
    url_hash(long_url, domain, channel) 重算原始哈希写回。
    该函数是纯函数,且这三个字段创建后不提供任何修改入口,
    所以能精确还原;若日后新增了改长链/域名/渠道的接口,
    必须同步改为「另存一份原始哈希」的方案。

    冲突处理:软删期间若同一长链被重新生成,活跃记录会占用同一个哈希,
    直接写回会撞唯一索引。此时返回 409,提示用户改用新短码,不做合并。
    """
    if not sl.is_deleted:
        return sl

    h = url_hash(sl.long_url, sl.domain or "", sl.channel or "")

    # 与全局唯一索引保持一致:除自己外任何记录占用该哈希都算冲突
    conflict = ShortLink.query.filter(
        ShortLink.url_hash == h,
        ShortLink.id != sl.id,
    ).first()
    if conflict is not None:
        raise ConflictError(
            f"该长链已存在新的短码 {conflict.short_code},无法恢复,请直接使用新短码"
        )

    sl.url_hash = h
    sl.is_deleted = False
    sl.deleted_at = None
    try:
        db.session.commit()
    except IntegrityError:
        # 上面的查重与写回之间存在竞态(并发 create 抢注同一长链),
        # 兜底转成 409,避免把唯一索引冲突暴露成 500。
        db.session.rollback()
        raise ConflictError("该长链已被重新生成,无法恢复,请直接使用新短码")
    return sl


def update_status(sl: ShortLink, status: str) -> None:
    if status not in (ShortLinkStatus.ENABLED, ShortLinkStatus.DISABLED):
        raise BadRequestError("status 仅支持 enabled / disabled")
    sl.status = status
    db.session.commit()


# 列表排序白名单:前端只传 key,永远不拼接原始 SQL
SORT_ORDERS = {
    "created_desc": (ShortLink.id.desc(),),
    "created_asc": (ShortLink.id.asc(),),
    "pv_desc": (ShortLink.visit_count.desc(), ShortLink.id.desc()),
    "last_visit_desc": (ShortLink.last_visit_at.desc(), ShortLink.id.desc()),
}
DEFAULT_SORT = "created_desc"


def list_for_user(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    include_deleted: bool = False,
    only_deleted: bool = False,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    channel: Optional[str] = None,
    domain: Optional[str] = None,
    sort: Optional[str] = None,
) -> tuple[list[ShortLink], int]:
    """分页列出用户的短链。

    include_deleted / only_deleted 互斥语义:
      - 默认:只返回活跃记录
      - include_deleted=True:活跃 + 已软删
      - only_deleted=True:只返回已软删(回收站视图),优先于 include_deleted

    筛选:
      - status / channel / domain 精确匹配
      - keyword 模糊匹配 short_code 或 long_url(空白串视为不筛选)
    """
    q = ShortLink.query.filter_by(user_id=user_id)
    if only_deleted:
        q = q.filter_by(is_deleted=True)
    elif not include_deleted:
        q = q.filter_by(is_deleted=False)
    if status:
        q = q.filter_by(status=status)
    if channel:
        q = q.filter_by(channel=channel)
    if domain:
        q = q.filter_by(domain=domain)
    kw = (keyword or "").strip()
    if kw:
        # LIKE 通配符按字面转义,避免用户输入的 % / _ 变成通配
        escaped = kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        q = q.filter(
            or_(
                ShortLink.short_code.like(like, escape="\\"),
                ShortLink.long_url.like(like, escape="\\"),
            )
        )
    total = q.count()
    order_by = SORT_ORDERS.get(sort or DEFAULT_SORT, SORT_ORDERS[DEFAULT_SORT])
    items = (
        q.order_by(*order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
