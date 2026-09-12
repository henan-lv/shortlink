"""短链生成 + 跳转 API。"""

from flask import Blueprint, current_app, redirect, request

from ..middleware.error import BadRequestError, NotFoundError
from ..schemas.short_link import CreateShortLinkRequest
from ..services import short_link as svc
from ..services import access_control
from ..utils.ip import get_real_ip
from ..utils.response import success
from ..extensions import db, get_redis
from ..middleware.auth import auth_optional
from ..services.rate_limit import check_rate_limit
from ..middleware.error import RateLimitError

bp = Blueprint("short_link", __name__)


@bp.route("/api/shortlinks", methods=["POST"])
@auth_optional
def create_short_link():
    """生成短链
    ---
    tags: [shortlinks]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [long_url]
          properties:
            long_url: {type: string}
            password: {type: string, description: "6-8 位"}
            effective_at: {type: string, format: date-time, description: "可选,默认立即生效"}
            expire_at: {type: string, format: date-time}
            click_limit: {type: integer}
    responses:
      201: {description: 创建成功}
      400: {description: 参数错误 / 恶意链接}
      429: {description: 触发限流}
    """
    payload = CreateShortLinkRequest().load(request.get_json(silent=True) or {})
    cfg = current_app.config
    if cfg.get("RATE_LIMIT_ENABLED"):
        ip = get_real_ip(request)
        redis_client = get_redis()
        result = check_rate_limit(
            redis_client, ip,
            max_per_minute=cfg["RATE_LIMIT_PER_MINUTE"],
            default_retry_after=cfg["RATE_LIMIT_RETRY_AFTER"],
        )
        if not result.allowed:
            raise RateLimitError("请求过于频繁", retry_after=result.retry_after)

    from flask import g as _g
    user_id = getattr(_g, "current_user", None) and _g.current_user.id
    sl = svc.create(
        long_url=payload["long_url"],
        password=payload.get("password"),
        effective_at=payload.get("effective_at"),
        expire_at=payload.get("expire_at"),
        click_limit=payload.get("click_limit"),
        user_id=user_id,
        domain=payload.get("domain"),
        channel=payload.get("channel"),
        advanced=payload.get("advanced"),
    )
    # 创建时 pv/uv 必然为 0,last_visit_at 必然 None
    sl.visit_count = sl.visit_count or 0
    # 优先用记录中的 domain(自定义域名),否则回退 BASE_DOMAIN
    base = sl.domain or (cfg.get("BASE_DOMAIN") or request.host_url.rstrip("/"))
    base = base.rstrip("/")
    full_url = f"{base}/s/{sl.short_code}"
    return success({
        "id": sl.id,
        "short_code": sl.short_code,
        "long_url": sl.long_url,
        "full_short_url": full_url,
        "status": sl.status,
        "has_password": bool(sl.password_hash),
        "pv": sl.visit_count or 0,
        "uv": 0,
        "click_limit": sl.click_limit,
        "created_at": sl.created_at.isoformat() if sl.created_at else None,
        "effective_at": sl.effective_at.isoformat() if sl.effective_at else None,
        "expire_at": sl.expire_at.isoformat() if sl.expire_at else None,
        "domain": sl.domain,
        "channel": sl.channel,
        "last_visit_at": sl.last_visit_at.isoformat() if sl.last_visit_at else None,
    }, http_status=201)


@bp.route("/s/<short_code>", methods=["GET"])
def redirect_short_link(short_code):
    """短码跳转(302 重定向)。
    ---
    tags: [redirect]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
    responses:
      302: {description: 重定向到原始长链}
      401: {description: 需要密码}
      403: {description: 已被标记恶意 / 未到生效时间}
      404: {description: 短码不存在 / 命中风控拦截(不暴露被封)}
      410: {description: 已过期 / 软删 / 停用 / 超限}
    """
    cfg = current_app.config
    # ---- 紧急熔断: 不查 DB 直接 503 ----
    if cfg.get("KILL_SWITCH_ENABLED"):
        from ..middleware.error import ServiceUnavailableError
        raise ServiceUnavailableError(cfg.get("KILL_SWITCH_MESSAGE") or "服务临时维护中")

    ip = get_real_ip(request)

    # ---- IP 白名单(PRD F3.4) ----
    if cfg.get("IP_WHITELIST_ENABLED"):
        from ..services.ip_whitelist import build_whitelist
        wl = build_whitelist(cfg.get("IP_WHITELIST_CIDRS"), True)
        if not wl.is_allowed(ip):
            from ..middleware.error import ForbiddenError
            raise ForbiddenError("IP 不在白名单")

    # ---- 反爬 UA(PRD F3.7) ----
    ua = request.headers.get("User-Agent") or ""
    from ..services.anti_bot import build_anti_bot
    ab = build_anti_bot(
        cfg.get("ANTI_BOT_UA_PATTERN"),
        cfg.get("ANTI_BOT_ENABLED", False),
        cfg.get("ANTI_BOT_UA_BLOCK", False),
    )
    bot = ab.check(ua)

    sl = svc.get_by_code(short_code)
    outcome, status = svc.redirect_pre_check(sl, cookies=request.cookies)
    if outcome == svc.RedirectOutcome.NOT_FOUND:
        raise NotFoundError("短码不存在")

    # ---- 访问控制 / 风控规则(PRD 模块三扩展) ----
    # 规则来源:生成页「高级设置」+ 统计页「一键拦截」。
    # 命中拦截时不写 click_logs(避免被刷爆库),只记 Redis 计数供统计展示。
    referer = request.headers.get("Referer")
    if cfg.get("ACCESS_CONTROL_ENABLED", True):
        rules = access_control.load_rules(short_code, sl.user_id)
        decision = access_control.evaluate(rules, ip=ip, ua=ua, referer=referer)
        if decision.blocked:
            access_control.record_hit(short_code, ip, observed=False)
            # 默认按 404 返回:对攻击者不暴露"该短码存在但被封"
            if cfg.get("ACCESS_CONTROL_BLOCK_STATUS", 404) == 403:
                from ..middleware.error import ForbiddenError
                raise ForbiddenError("访问被拒绝")
            raise NotFoundError("短码不存在")
        if decision.observed:
            # 观察态:放行但记一笔,便于先看再决定是否升级为拦截
            access_control.record_hit(short_code, ip, observed=True)

    if outcome == svc.RedirectOutcome.MALICIOUS:
        from ..middleware.error import ForbiddenError
        raise ForbiddenError("链接已被标记恶意")
    if outcome == svc.RedirectOutcome.GONE:
        from ..middleware.error import GoneError
        raise GoneError("短链已失效")
    if outcome == svc.RedirectOutcome.UNAUTHORIZED:
        from ..middleware.error import UnauthorizedError
        raise UnauthorizedError("需要密码验证")
    if outcome == svc.RedirectOutcome.NOT_EFFECTIVE:
        from ..middleware.error import ForbiddenError
        raise ForbiddenError("短链尚未生效")

    # OK -> 记录点击 + 302(可疑 UA 仅在非 block 模式下跳过 PV)
    if not bot.suspicious:
        svc.record_click(
            sl,
            ip=ip,
            user_agent=request.headers.get("User-Agent"),
            referer=referer,
        )
    return redirect(sl.long_url, code=302)
