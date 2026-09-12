"""访问统计 API(PRD 模块二)。

包含:
  - GET /api/stats/overview                     全站总览聚合(按登录用户)
  - GET /api/shortlinks/<code>/stats            单链聚合指标(PV/UV/状态)
  - GET /api/shortlinks/<code>/visitors         访问来源明细(IP / UA / Referer 聚合)
  - GET /api/shortlinks/<code>/trend            点击趋势(F2.1)
  - GET /api/shortlinks/<code>/breakdown        来源分类 / 设备 / 地理(F2.2 F2.3 F2.4)
  - GET /api/shortlinks/<code>/realtime         实时统计(F2.6)
  - GET /api/shortlinks/<code>/export           导出 CSV(F2.7)

鉴权约定(重要):
  链接的 long_url 属于归属者的私有信息,且密码保护(F3.3)/ 停用 / 过期
  不应被统计接口绕过。因此统计接口都要求登录并只允许归属者访问明细;
  唯一的例外是 /stats 对「当前可匿名正常跳转」的链接放行聚合值(不含 long_url),
  以支持未登录生成的公开短链查看自己的数据。
"""

import csv
import io
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, Response, current_app, g, request
from sqlalchemy import func

from ..extensions import db
from ..middleware.auth import auth_optional, auth_required
from ..middleware.error import BadRequestError, NotFoundError
from ..models import ClickLog, ShortLink, ShortLinkStatus
from ..services import access_control
from ..services import analytics
from ..services import short_link as svc
from ..utils.response import success

bp = Blueprint("stats", __name__)

# 允许聚合的维度 → ClickLog 列
_DIM_COLUMNS = {
    "ip": ClickLog.ip,
    "ua": ClickLog.user_agent,
    "referer": ClickLog.referer,
}

# breakdown 支持的分类维度
_BREAKDOWN_DIMS = {
    "device": "设备类型",
    "os": "操作系统",
    "browser": "浏览器",
    "referer_type": "来源分类",
    "geo": "地理分布",
}

# 明细窗口上限(天),与 access_control 的拦截计数保留期保持一致
_MAX_WINDOW_DAYS = 90

# 导出上限:超过这个行数只导出最近的部分,避免一次性把库拉爆
_EXPORT_MAX_ROWS = 20000


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _int_arg(raw, default: int, lo: int, hi: int) -> int:
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(val, hi))


def _owned_or_404(short_code: str) -> ShortLink:
    """取当前登录用户名下的链接,非归属者一律当作「不存在」。

    与 get_visitors 保持同一套语义:不泄露短码是否存在。
    """
    user = getattr(g, "current_user", None)
    sl = svc.get_active_by_code(short_code)
    if sl is None or user is None or sl.user_id != user.id:
        raise NotFoundError("短码不存在")
    return sl


def _full_url(sl: ShortLink) -> str:
    base = sl.domain or current_app.config.get("BASE_DOMAIN") or current_app.config["PREFERRED_URL_SCHEME"] + "://" + request.host
    return f"{base.rstrip(chr(47))}/s/{sl.short_code}"


# ==========================================================================
# 总览
# ==========================================================================

@bp.route("/api/stats/overview", methods=["GET"])
@auth_required
def get_overview():
    """当前用户的全站总览聚合(指挥中心)。

    全部数字都走 SQL 后端聚合,与单链 click_logs / Redis 拦截计数一致。
    返回多维 Top 列,前端用来做"对比卡",不再"拉 100 条在前端求和"。
    ---
    tags: [stats]
    parameters:
      - in: query
        name: days
        type: integer
        default: 7
        description: 统计窗口天数(1-90),影响 PV/UV/拦截/Top
    responses:
      200: {description: 总览指标 + 多维 Top10}
      401: {description: 未登录}
    """
    user = g.current_user
    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=90)
    since = _now() - timedelta(days=days)

    alive = ShortLink.query.filter_by(user_id=user.id, is_deleted=False)
    total = alive.count()
    enabled = alive.filter_by(status=ShortLinkStatus.ENABLED).count()
    deleted = ShortLink.query.filter_by(user_id=user.id, is_deleted=True).count()

    # 窗口内的 PV(全部 click_logs 之和)
    pv = (
        db.session.query(func.count())
        .select_from(ClickLog)
        .join(ShortLink, ShortLink.short_code == ClickLog.short_code)
        .filter(
            ShortLink.user_id == user.id,
            ShortLink.is_deleted.is_(False),
            ClickLog.clicked_at >= since,
        )
        .scalar()
        or 0
    )

    # 窗口内每条链的 UV(IP 去重)
    uv_rows = (
        db.session.query(
            ClickLog.short_code,
            func.count(func.distinct(ClickLog.ip)).label("uv"),
        )
        .join(ShortLink, ShortLink.short_code == ClickLog.short_code)
        .filter(
            ShortLink.user_id == user.id,
            ShortLink.is_deleted.is_(False),
            ClickLog.clicked_at >= since,
        )
        .group_by(ClickLog.short_code)
        .all()
    )
    uv_map = {code: int(n) for code, n in uv_rows}

    # 窗口内每条链的 PV(用于 Top PV,只统计窗口内新产生的点击)
    pv_rows = (
        db.session.query(
            ClickLog.short_code,
            func.count().label("pv"),
        )
        .join(ShortLink, ShortLink.short_code == ClickLog.short_code)
        .filter(
            ShortLink.user_id == user.id,
            ShortLink.is_deleted.is_(False),
            ClickLog.clicked_at >= since,
        )
        .group_by(ClickLog.short_code)
        .all()
    )
    pv_window_map = {code: int(n) for code, n in pv_rows}

    # 窗口内全站去重 UV(同一访客访问多条链接只算 1)
    unique_visitors = (
        db.session.query(func.count(func.distinct(ClickLog.ip)))
        .join(ShortLink, ShortLink.short_code == ClickLog.short_code)
        .filter(
            ShortLink.user_id == user.id,
            ShortLink.is_deleted.is_(False),
            ClickLog.clicked_at >= since,
        )
        .scalar()
        or 0
    )

    # 该用户所有非删除短码(用于 Redis 拦截计数聚合)
    user_codes = [
        c for (c,) in db.session.query(ShortLink.short_code)
        .filter(ShortLink.user_id == user.id, ShortLink.is_deleted.is_(False))
        .all()
    ]
    blocked_map = access_control.get_user_blocked_totals(user_codes, days)
    blocked_total = sum(blocked_map.values())

    # 把 short_code 列表 + 指标 map 转成 dict 方便组装 Top
    sl_rows = alive.all()
    sl_by_code = {sl.short_code: sl for sl in sl_rows}

    def _pack_top(sort_key, value_map, limit=10):
        rows = []
        for code, sl in sl_by_code.items():
            v = value_map.get(code, 0)
            if v <= 0:
                continue
            rows.append((code, sl, v))
        rows.sort(key=sort_key, reverse=True)
        out = []
        for code, sl, v in rows[:limit]:
            out.append({
                "id": sl.id,
                "short_code": code,
                "long_url": sl.long_url,
                "full_short_url": _full_url(sl),
                "value": int(v),
                "status": sl.status,
                "has_password": bool(sl.password_hash),
                "last_visit_at": sl.last_visit_at.isoformat() if sl.last_visit_at else None,
                "expire_at": sl.expire_at.isoformat() if sl.expire_at else None,
            })
        return out

    # Top PV(窗口内 PV 排序;并列时按累计 visit_count,再按 id)
    top_pv = _pack_top(
        lambda r: (r[2], sl_by_code[r[0]].visit_count or 0, -(r[1].id or 0)),
        pv_window_map,
    )
    # Top UV(窗口内独立访客)
    top_uv = _pack_top(lambda r: (r[2], r[1].id), uv_map)
    # Top 拦截(Redis 计数)
    top_blocked = _pack_top(lambda r: (r[2], r[1].id), blocked_map)
    # Top 即将过期(未来 7 天内过期),按剩余时间升序(最紧迫在前)
    now = _now()
    expiring_cutoff = now + timedelta(days=7)
    expiring_rows = []
    for sl in sl_rows:
        if not sl.expire_at or sl.expire_at < now or sl.expire_at > expiring_cutoff:
            continue
        expiring_rows.append(sl)
    expiring_rows.sort(key=lambda s: (s.expire_at, -(s.id or 0)))
    top_expiring = [
        {
            "id": sl.id,
            "short_code": sl.short_code,
            "long_url": sl.long_url,
            "full_short_url": _full_url(sl),
            "expire_at": sl.expire_at.isoformat(),
            "status": sl.status,
        }
        for sl in expiring_rows[:10]
    ]

    # 兼容旧字段 top(按 PV 全期累计排序)
    top_full_pv = sorted(sl_rows, key=lambda s: (-(s.visit_count or 0), -(s.id or 0)))[:10]
    top_legacy = [
        {
            "id": sl.id,
            "short_code": sl.short_code,
            "long_url": sl.long_url,
            "full_short_url": _full_url(sl),
            "pv": sl.visit_count or 0,
            "uv": uv_map.get(sl.short_code, 0),
            "status": sl.status,
            "has_password": bool(sl.password_hash),
            "last_visit_at": sl.last_visit_at.isoformat() if sl.last_visit_at else None,
            "created_at": sl.created_at.isoformat() if sl.created_at else None,
        }
        for sl in top_full_pv
    ]

    healthy_ratio = round(enabled / total, 4) if total else 0
    avg_pv = round(pv / total, 2) if total else 0

    return success({
        # 链接统计
        "total": total,
        "enabled": enabled,
        "disabled": total - enabled,
        "deleted": deleted,
        "healthy_ratio": healthy_ratio,         # 健康占比(enabled/total)
        # 流量(全部基于窗口 days)
        "days": days,
        "pv": int(pv),
        "uv_sum": sum(uv_map.values()),
        "uv": int(unique_visitors),
        "avg_pv_per_link": avg_pv,              # 平均 PV / 链接
        # 风控
        "blocked_total": blocked_total,
        # 多维 Top
        "top_pv": top_pv,
        "top_uv": top_uv,
        "top_blocked": top_blocked,
        "top_expiring": top_expiring,
        # 兼容旧字段
        "top": top_legacy,
    })


# ==========================================================================
# 单链聚合指标
# ==========================================================================

@bp.route("/api/shortlinks/<short_code>/stats", methods=["GET"])
@auth_optional
def get_stats(short_code):
    """获取访问统计

    long_url / full_short_url 只对链接归属者返回。非归属者要读聚合值,
    必须满足「该链接当前能匿名正常跳转」;带密码、停用、过期、未生效、
    已删除的链接一律返回 404,避免绕过 F3.1 / F3.2 / F3.3 的保护。
    ---
    tags: [stats]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
    responses:
      200: {description: 统计信息}
      404: {description: 短码不存在或无权查看}
    """
    user = getattr(g, "current_user", None)
    sl = svc.get_active_by_code(short_code)
    if sl is None:
        raise NotFoundError("短码不存在")

    is_owner = user is not None and sl.user_id is not None and sl.user_id == user.id
    if not is_owner:
        outcome, _ = svc.redirect_pre_check(sl)
        if outcome != svc.RedirectOutcome.OK:
            raise NotFoundError("短码不存在")

    data = {
        "short_code": sl.short_code,
        "pv": sl.visit_count,
        "uv": svc.get_uv(sl),
        "status": sl.status,
        "has_password": bool(sl.password_hash),
        "created_at": sl.created_at.isoformat() if sl.created_at else None,
        "effective_at": sl.effective_at.isoformat() if sl.effective_at else None,
        "expire_at": sl.expire_at.isoformat() if sl.expire_at else None,
        "last_visit_at": sl.last_visit_at.isoformat() if sl.last_visit_at else None,
        "click_limit": sl.click_limit,
        "is_owner": is_owner,
    }
    if is_owner:
        data["long_url"] = sl.long_url
        data["full_short_url"] = _full_url(sl)
    return success(data)


# ==========================================================================
# 访问来源明细(IP / UA / Referer)+ 一键拦截
# ==========================================================================

@bp.route("/api/shortlinks/<short_code>/visitors", methods=["GET"])
@auth_required
def get_visitors(short_code):
    """访问来源明细(按 IP / UA / Referer 聚合)

    用于在统计页「看见」是谁在访问,并据此一键加入拦截名单。
    IP 属个人信息,故本接口要求登录且仅限链接归属者访问。
    ---
    tags: [stats]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
      - in: query
        name: dim
        type: string
        enum: [ip, ua, referer]
        default: ip
      - in: query
        name: days
        type: integer
        default: 7
        description: 统计窗口天数(1-90)
      - in: query
        name: limit
        type: integer
        default: 20
        description: 返回条数(1-100)
    responses:
      200: {description: 访问来源列表 + 当前生效规则 + 拦截计数}
      400: {description: dim 不合法}
      401: {description: 未登录}
      404: {description: 短码不存在或无权查看}
    """
    sl = _owned_or_404(short_code)

    dim = (request.args.get("dim") or "ip").strip().lower()
    if dim not in _DIM_COLUMNS:
        raise BadRequestError("dim 仅支持 ip / ua / referer")

    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=_MAX_WINDOW_DAYS)
    limit = _int_arg(request.args.get("limit"), default=20, lo=1, hi=100)

    col = _DIM_COLUMNS[dim]
    since = _now() - timedelta(days=days)

    total = (
        db.session.query(func.count())
        .select_from(ClickLog)
        .filter(ClickLog.short_code == short_code, ClickLog.clicked_at >= since)
        .scalar()
        or 0
    )

    rows = (
        db.session.query(
            col.label("val"),
            func.count().label("pv"),
            func.min(ClickLog.clicked_at).label("first_at"),
            func.max(ClickLog.clicked_at).label("last_at"),
        )
        .filter(ClickLog.short_code == short_code, ClickLog.clicked_at >= since)
        .group_by(col)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )

    # 已拦截 IP 的计数(被拦的请求不写 click_logs,只能从 Redis 计数拿)
    hits = access_control.get_hit_stats(short_code, days)
    blocked_ip_counts = {x["ip"]: x["count"] for x in hits.get("top_ips", [])}

    # 生效规则(带 id,供前端解封)
    rules = access_control.query_active_rules(short_code, sl.user_id)
    active_rules = [r.to_dict() for r in rules]

    items = []
    for r in rows:
        raw = r.val
        matched = None
        if raw:
            matched = access_control.find_matching_rule(
                rules,
                ip=raw if dim == "ip" else None,
                ua=raw if dim == "ua" else None,
                referer=raw if dim == "referer" else None,
            )
        items.append({
            "value": raw if raw not in (None, "") else "(空)",
            "raw": raw,
            "pv": r.pv,
            "ratio": round(r.pv / total, 4) if total else 0,
            "first_at": r.first_at.isoformat() if r.first_at else None,
            "last_at": r.last_at.isoformat() if r.last_at else None,
            "blocked": matched is not None,
            # 拦截计数只按 IP 维度记录,其他维度没有这个数据
            "blocked_count": blocked_ip_counts.get(raw, 0) if dim == "ip" else None,
        })

    return success({
        "short_code": short_code,
        "dim": dim,
        "days": days,
        "total": total,
        "items": items,
        "rules": active_rules,
        "hits": hits,
    })


# ==========================================================================
# F2.1 点击趋势
# ==========================================================================

_TREND_GRANULARITIES = ("hour", "day", "week", "month")


def _bucket_expr(granularity: str):
    """返回按小时 / 天分桶的 SQL 表达式。

    两种方言都返回字符串,避免 MySQL 的 date 与 SQLite 的 text 类型不一致:
      - SQLite : strftime
      - MySQL  : DATE_FORMAT
    周 / 月不在 SQL 里分桶,而是把天级结果在 Python 侧合并(见 _series)。
    """
    fmt = "%Y-%m-%dT%H:00" if granularity == "hour" else "%Y-%m-%d"
    if db.engine.dialect.name == "sqlite":
        return func.strftime(fmt, ClickLog.clicked_at)
    return func.date_format(ClickLog.clicked_at, fmt)


def _rollup_key(day_str: str, granularity: str) -> str:
    d = datetime.strptime(day_str, "%Y-%m-%d").date()
    if granularity == "week":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return d.strftime("%Y-%m")


def _bucket_series(short_code: str, since: datetime, granularity: str) -> dict:
    """返回 {bucket: {"pv": n, "ips": set()}}。

    PV 与 UV 分两条查询:
      - PV 用 GROUP BY 直接算;
      - UV 取 DISTINCT (bucket, ip),在 Python 侧按 bucket 去重。
        这样周 / 月合并时可以把 IP 集合求并集,而不是把每天的 UV 相加
        (后者会把跨天的同一访客重复计数)。
    """
    bucket = _bucket_expr(granularity)
    window = (ClickLog.short_code == short_code, ClickLog.clicked_at >= since)

    out: dict[str, dict] = {}

    pv_rows = (
        db.session.query(bucket.label("b"), func.count().label("pv"))
        .filter(*window)
        .group_by(bucket)
        .all()
    )
    for b, pv in pv_rows:
        out.setdefault(str(b), {"pv": 0, "ips": set()})["pv"] = int(pv)

    uv_rows = (
        db.session.query(bucket.label("b"), ClickLog.ip)
        .filter(*window)
        .distinct()
        .all()
    )
    for b, ip in uv_rows:
        out.setdefault(str(b), {"pv": 0, "ips": set()})["ips"].add(ip)

    return out


def _fill_gaps(points: list, since: datetime, until: datetime, granularity: str) -> list:
    """把没有点击的时间点补成 0,保证折线是连续的。"""
    have = {p["t"]: p for p in points}
    out = []
    if granularity == "hour":
        cur = since.replace(minute=0, second=0, microsecond=0)
        while cur <= until:
            key = cur.strftime("%Y-%m-%dT%H:00")
            out.append(have.get(key) or {"t": key, "pv": 0, "uv": 0})
            cur += timedelta(hours=1)
        return out
    if granularity == "day":
        cur = since.date()
        while cur <= until.date():
            key = cur.strftime("%Y-%m-%d")
            out.append(have.get(key) or {"t": key, "pv": 0, "uv": 0})
            cur += timedelta(days=1)
        return out
    # week / month:只保留实际有数据的桶,粒度粗,不值得再造一套日历
    return [have[k] for k in sorted(have)]


def _series(short_code: str, since: datetime, granularity: str) -> list:
    if granularity == "hour":
        buckets = _bucket_series(short_code, since, "hour")
        return [
            {"t": b, "pv": v["pv"], "uv": len(v["ips"])}
            for b, v in sorted(buckets.items())
        ]

    days = _bucket_series(short_code, since, "day")
    if granularity == "day":
        return [
            {"t": b, "pv": v["pv"], "uv": len(v["ips"])}
            for b, v in sorted(days.items())
        ]

    merged: dict[str, dict] = {}
    for b, v in sorted(days.items()):
        cur = merged.setdefault(_rollup_key(b, granularity), {"pv": 0, "ips": set()})
        cur["pv"] += v["pv"]
        cur["ips"] |= v["ips"]
    return [
        {"t": k, "pv": v["pv"], "uv": len(v["ips"])}
        for k, v in sorted(merged.items())
    ]


@bp.route("/api/shortlinks/<short_code>/trend", methods=["GET"])
@auth_required
def get_trend(short_code):
    """点击趋势(PRD F2.1)

    维度支持 小时 / 天 / 周 / 月,数据与明细一致(同一份 click_logs)。
    ---
    tags: [stats]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
      - in: query
        name: granularity
        type: string
        enum: [hour, day, week, month]
        default: day
      - in: query
        name: days
        type: integer
        default: 7
        description: 统计窗口天数(1-90)
    responses:
      200: {description: 时间点 + PV/UV}
      400: {description: granularity 不合法}
      401: {description: 未登录}
      404: {description: 短码不存在或无权查看}
    """
    _owned_or_404(short_code)

    granularity = (request.args.get("granularity") or "day").strip().lower()
    if granularity not in _TREND_GRANULARITIES:
        raise BadRequestError("granularity 仅支持 " + " / ".join(_TREND_GRANULARITIES))

    # 小时维度看不了太久,否则点数过多
    max_days = 7 if granularity == "hour" else _MAX_WINDOW_DAYS
    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=max_days)

    until = _now()
    since = until - timedelta(days=days)
    points = _fill_gaps(_series(short_code, since, granularity), since, until, granularity)

    return success({
        "short_code": short_code,
        "granularity": granularity,
        "days": days,
        "points": points,
        "total_pv": sum(p["pv"] for p in points),
    })


# ==========================================================================
# F2.2 来源分类 / F2.3 地理分布 / F2.4 设备分析
# ==========================================================================

def _pack(acc: dict, total: int, limit: int = 8) -> list:
    rows = sorted(acc.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [
        {"value": k, "pv": int(v), "ratio": round(v / total, 4) if total else 0}
        for k, v in rows
    ]


@bp.route("/api/shortlinks/<short_code>/breakdown", methods=["GET"])
@auth_required
def get_breakdown(short_code):
    """按分类维度聚合访问(来源分类 / 设备 / 系统 / 浏览器 / 地理)。

    UA 与 Referer 的分类在 Python 侧做(SQL 里没法解析),
    所以先按原始值 GROUP BY 再归类合并,避免把整表行拉回来。
    ---
    tags: [stats]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
      - in: query
        name: by
        type: string
        enum: [device, os, browser, referer_type, geo]
        default: device
      - in: query
        name: days
        type: integer
        default: 7
        description: 统计窗口天数(1-90)
      - in: query
        name: level
        type: string
        enum: [country, province, city]
        default: country
        description: 仅 by=geo 时生效
    responses:
      200: {description: 分类占比列表}
      400: {description: by / level 不合法}
      401: {description: 未登录}
      404: {description: 短码不存在或无权查看}
    """
    _owned_or_404(short_code)

    by = (request.args.get("by") or "device").strip().lower()
    if by not in _BREAKDOWN_DIMS:
        raise BadRequestError("by 仅支持 " + " / ".join(_BREAKDOWN_DIMS))

    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=_MAX_WINDOW_DAYS)
    since = _now() - timedelta(days=days)
    window = (ClickLog.short_code == short_code, ClickLog.clicked_at >= since)

    total = (
        db.session.query(func.count())
        .select_from(ClickLog)
        .filter(*window)
        .scalar()
        or 0
    )

    acc: dict[str, int] = {}

    if by in ("device", "os", "browser"):
        rows = (
            db.session.query(ClickLog.user_agent, func.count())
            .filter(*window)
            .group_by(ClickLog.user_agent)
            .all()
        )
        for ua, cnt in rows:
            key = analytics.parse_ua(ua)[by]
            acc[key] = acc.get(key, 0) + int(cnt)
    elif by == "referer_type":
        rows = (
            db.session.query(ClickLog.referer, func.count())
            .filter(*window)
            .group_by(ClickLog.referer)
            .all()
        )
        for ref, cnt in rows:
            key = analytics.classify_referer(ref)
            acc[key] = acc.get(key, 0) + int(cnt)
    else:  # geo
        level = (request.args.get("level") or "country").strip().lower()
        if level not in ("country", "province", "city"):
            raise BadRequestError("level 仅支持 country / province / city")
        rows = (
            db.session.query(ClickLog.ip, func.count())
            .filter(*window)
            .group_by(ClickLog.ip)
            .all()
        )
        for ip, cnt in rows:
            key = analytics.lookup_ip(ip, level)
            acc[key] = acc.get(key, 0) + int(cnt)

    payload = {
        "short_code": short_code,
        "by": by,
        "label": _BREAKDOWN_DIMS[by],
        "days": days,
        "total": total,
        "items": _pack(acc, total),
    }
    if by == "geo":
        # 没有 IP 库时只有「内网 / 未知」两类,前端据此提示需要接数据源
        payload["available"] = analytics.geo_available()
    return success(payload)


# ==========================================================================
# 总览 · 异常雷达
# ==========================================================================

@bp.route("/api/stats/overview/alerts", methods=["GET"])
@auth_required
def get_overview_alerts():
    """总览页"异常雷达"。一句话告诉运营哪里出了问题。

    四类:
      - expiring  : 未来 7 天内过期
      - high_block: 近 days 天被拦截 >= 20 次
      - zombie    : 启用中,但 30 天以上无访问
      - near_cap  : 启用中,click_limit 已用 >= 90%

    每类最多返回 10 条详情,summary 同步返回全量计数,前端据此显示
    "3 条临期 / 1 条触达上限" 这种概览。
    ---
    tags: [stats]
    parameters:
      - in: query
        name: days
        type: integer
        default: 7
        description: 拦截计数窗口(1-90)
      - in: query
        name: block_threshold
        type: integer
        default: 20
        description: 进入 high_block 列表的最小拦截次数
    responses:
      200: {description: 四类异常列表 + summary}
      401: {description: 未登录}
    """
    user = g.current_user
    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=90)
    block_threshold = _int_arg(request.args.get("block_threshold"), default=20, lo=1, hi=10000)

    sl_rows = (
        ShortLink.query.filter_by(user_id=user.id, is_deleted=False)
        .order_by(ShortLink.id.asc())
        .all()
    )
    codes = [sl.short_code for sl in sl_rows]
    blocked_map = access_control.get_user_blocked_totals(codes, days)

    now = _now()

    # ===== 临期 =====
    expiring_cutoff = now + timedelta(days=7)
    expiring_all = [
        sl for sl in sl_rows
        if sl.expire_at and now <= sl.expire_at <= expiring_cutoff
    ]
    expiring_all.sort(key=lambda s: (s.expire_at, -(s.id or 0)))
    expiring_items = [
        {
            "id": sl.id,
            "short_code": sl.short_code,
            "long_url": sl.long_url,
            "full_short_url": _full_url(sl),
            "expire_at": sl.expire_at.isoformat(),
            "status": sl.status,
        }
        for sl in expiring_all[:10]
    ]

    # ===== 高拦截 =====
    high_block_all = [
        (code, cnt) for code, cnt in blocked_map.items() if cnt >= block_threshold
    ]
    high_block_all.sort(key=lambda x: -x[1])
    sl_by_code = {sl.short_code: sl for sl in sl_rows}
    high_block_items = [
        {
            "id": sl_by_code[code].id,
            "short_code": code,
            "long_url": sl_by_code[code].long_url,
            "full_short_url": _full_url(sl_by_code[code]),
            "blocked_count": int(cnt),
            "status": sl_by_code[code].status,
        }
        for code, cnt in high_block_all[:10]
        if code in sl_by_code
    ]

    # ===== 僵尸 =====
    zombie_cutoff = now - timedelta(days=30)
    zombie_all = []
    for sl in sl_rows:
        if sl.status != ShortLinkStatus.ENABLED:
            continue
        if sl.last_visit_at is None:
            # 从未访问过,且创建已超过 30 天
            if sl.created_at and sl.created_at <= zombie_cutoff:
                zombie_all.append(sl)
        elif sl.last_visit_at < zombie_cutoff:
            zombie_all.append(sl)
    zombie_all.sort(key=lambda s: (s.last_visit_at or s.created_at, -(s.id or 0)))
    zombie_items = [
        {
            "id": sl.id,
            "short_code": sl.short_code,
            "long_url": sl.long_url,
            "full_short_url": _full_url(sl),
            "last_visit_at": sl.last_visit_at.isoformat() if sl.last_visit_at else None,
            "created_at": sl.created_at.isoformat() if sl.created_at else None,
        }
        for sl in zombie_all[:10]
    ]

    # ===== 触达上限 =====
    near_cap_all = []
    for sl in sl_rows:
        if not sl.click_limit or sl.click_limit <= 0:
            continue
        ratio = (sl.visit_count or 0) / sl.click_limit
        if ratio >= 0.9:
            near_cap_all.append((sl, ratio))
    near_cap_all.sort(key=lambda x: -x[1])
    near_cap_items = [
        {
            "id": sl.id,
            "short_code": sl.short_code,
            "long_url": sl.long_url,
            "full_short_url": _full_url(sl),
            "pv": sl.visit_count or 0,
            "click_limit": sl.click_limit,
            "ratio": round(ratio, 3),
        }
        for sl, ratio in near_cap_all[:10]
    ]

    return success({
        "days": days,
        "block_threshold": block_threshold,
        "summary": {
            "expiring": len(expiring_all),
            "high_block": len(high_block_all),
            "zombie": len(zombie_all),
            "near_cap": len(near_cap_all),
        },
        "expiring": expiring_items,
        "high_block": high_block_items,
        "zombie": zombie_items,
        "near_cap": near_cap_items,
    })


# ==========================================================================



# ==========================================================================
# 总览 · 跨链接聚合(趋势 / 来源分类 / 实时)
# ==========================================================================
#
# 与「单链接」接口的区别:
#   - 数据源不是单条 ClickLog.short_code,而是 ClickLog JOIN ShortLink ON user_id
#   - 返回结构专门为总览页卡片设计(更紧凑,不带 short_code 列)
#   - 鉴权:必须登录;只统计当前用户名下的短码,不会跨用户泄露
#
# 为什么不在前端循环调用单链接口:
#   - 用户有 100+ 链接时,前端会发起 100+ 次请求,数据库被扇出打爆
#   - 后端一次聚合 = 一次 GROUP BY,O(N) 行变成 O(类目) 行
# --------------------------------------------------------------------------


def _user_window(user_id: int, since: datetime):
    """返回总览聚合需要的 click_logs 过滤条件(JOIN 当前用户)。"""
    return (
        ClickLog.short_code.in_(
            db.session.query(ShortLink.short_code).filter(
                ShortLink.user_id == user_id,
                ShortLink.is_deleted.is_(False),
            )
        ),
        ClickLog.clicked_at >= since,
    )


def _user_bucket_series(user_id: int, since: datetime, granularity: str) -> dict:
    """按用户聚合的 {bucket: {"pv": n, "ips": set()}}。"""
    bucket = _bucket_expr(granularity)
    window = _user_window(user_id, since)

    out: dict[str, dict] = {}

    pv_rows = (
        db.session.query(bucket.label("b"), func.count().label("pv"))
        .filter(*window)
        .group_by(bucket)
        .all()
    )
    for b, pv in pv_rows:
        out.setdefault(str(b), {"pv": 0, "ips": set()})["pv"] = int(pv)

    uv_rows = (
        db.session.query(bucket.label("b"), ClickLog.ip)
        .filter(*window)
        .distinct()
        .all()
    )
    for b, ip in uv_rows:
        out.setdefault(str(b), {"pv": 0, "ips": set()})["ips"].add(ip)

    return out


def _user_series(user_id: int, since: datetime, granularity: str) -> list:
    """跨链接聚合的时间序列,语义与 _series 完全一致。"""
    if granularity == "hour":
        buckets = _user_bucket_series(user_id, since, "hour")
        return [
            {"t": b, "pv": v["pv"], "uv": len(v["ips"])}
            for b, v in sorted(buckets.items())
        ]

    days = _user_bucket_series(user_id, since, "day")
    if granularity == "day":
        return [
            {"t": b, "pv": v["pv"], "uv": len(v["ips"])}
            for b, v in sorted(days.items())
        ]

    merged: dict[str, dict] = {}
    for b, v in sorted(days.items()):
        cur = merged.setdefault(_rollup_key(b, granularity), {"pv": 0, "ips": set()})
        cur["pv"] += v["pv"]
        cur["ips"] |= v["ips"]
    return [
        {"t": k, "pv": v["pv"], "uv": len(v["ips"])}
        for k, v in sorted(merged.items())
    ]


@bp.route("/api/stats/overview/trend", methods=["GET"])
@auth_required
def get_overview_trend():
    """总览页的跨链接点击趋势(PRD F2.1 在总览维度的展示)。

    与单链 /trend 的差别:
      - 统计全部短码的合计,而不是单条
      - 鉴权必须是登录用户(否则无法归属)
    ---
    tags: [stats]
    parameters:
      - in: query
        name: granularity
        type: string
        enum: [hour, day, week, month]
        default: day
      - in: query
        name: days
        type: integer
        default: 7
    responses:
      200: {description: 时间序列 + 合计 PV/UV}
      401: {description: 未登录}
    """
    user = g.current_user
    if user is None:
        raise NotFoundError("未登录")

    granularity = (request.args.get("granularity") or "day").strip().lower()
    if granularity not in _TREND_GRANULARITIES:
        raise BadRequestError("granularity 仅支持 " + " / ".join(_TREND_GRANULARITIES))

    max_days = 7 if granularity == "hour" else _MAX_WINDOW_DAYS
    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=max_days)

    until = _now()
    since = until - timedelta(days=days)
    points = _fill_gaps(_user_series(user.id, since, granularity), since, until, granularity)

    return success({
        "granularity": granularity,
        "days": days,
        "points": points,
        "total_pv": sum(p["pv"] for p in points),
        "total_uv": sum(p["uv"] for p in points),
    })


@bp.route("/api/stats/overview/breakdown", methods=["GET"])
@auth_required
def get_overview_breakdown():
    """总览页的跨链接来源分类 / 设备 / 浏览器 / 系统 / 地理(PRD F2.2-F2.4)。

    同一份逻辑、单链版本的「精简版」:不要 short_code,只返回类目占比。
    """
    user = g.current_user
    if user is None:
        raise NotFoundError("未登录")

    by = (request.args.get("by") or "device").strip().lower()
    if by not in _BREAKDOWN_DIMS:
        raise BadRequestError("by 仅支持 " + " / ".join(_BREAKDOWN_DIMS))

    days = _int_arg(request.args.get("days"), default=7, lo=1, hi=_MAX_WINDOW_DAYS)
    since = _now() - timedelta(days=days)
    window = _user_window(user.id, since)

    total = (
        db.session.query(func.count())
        .select_from(ClickLog)
        .filter(*window)
        .scalar()
        or 0
    )

    acc: dict[str, int] = {}

    if by in ("device", "os", "browser"):
        rows = (
            db.session.query(ClickLog.user_agent, func.count())
            .filter(*window)
            .group_by(ClickLog.user_agent)
            .all()
        )
        for ua, cnt in rows:
            key = analytics.parse_ua(ua)[by]
            acc[key] = acc.get(key, 0) + int(cnt)
    elif by == "referer_type":
        rows = (
            db.session.query(ClickLog.referer, func.count())
            .filter(*window)
            .group_by(ClickLog.referer)
            .all()
        )
        for ref, cnt in rows:
            key = analytics.classify_referer(ref)
            acc[key] = acc.get(key, 0) + int(cnt)
    else:  # geo
        level = (request.args.get("level") or "country").strip().lower()
        if level not in ("country", "province", "city"):
            raise BadRequestError("level 仅支持 country / province / city")
        rows = (
            db.session.query(ClickLog.ip, func.count())
            .filter(*window)
            .group_by(ClickLog.ip)
            .all()
        )
        for ip, cnt in rows:
            key = analytics.lookup_ip(ip, level)
            acc[key] = acc.get(key, 0) + int(cnt)

    payload = {
        "by": by,
        "label": _BREAKDOWN_DIMS[by],
        "days": days,
        "total": total,
        "items": _pack(acc, total),
    }
    if by == "geo":
        payload["available"] = analytics.geo_available()
    return success(payload)


@bp.route("/api/stats/overview/realtime", methods=["GET"])
@auth_required
def get_overview_realtime():
    """总览页「最近 30 分钟」实时观察(PRD F2.6 在总览维度的展示)。

    返回:
      - count        : 当前窗口内跨链接点击量
      - peak_per_min : 窗口内最活跃的分钟点击量
      - top_links    : 当前窗口内点击量 Top 5 短码(用于快速定位爆款)
      - latest       : 最近 10 条跨用户点击(用于「有人在访问」指示)
    """
    user = g.current_user
    if user is None:
        raise NotFoundError("未登录")

    minutes = _int_arg(request.args.get("minutes"), default=30, lo=1, hi=1440)
    since = _now() - timedelta(minutes=minutes)
    window = _user_window(user.id, since)

    count = (
        db.session.query(func.count())
        .select_from(ClickLog)
        .filter(*window)
        .scalar()
        or 0
    )

    # Top 5 短码
    from sqlalchemy import desc
    top_rows = (
        db.session.query(ClickLog.short_code, func.count().label("pv"))
        .filter(*window)
        .group_by(ClickLog.short_code)
        .order_by(desc("pv"))
        .limit(5)
        .all()
    )
    top_links = [
        {"short_code": sc, "pv": int(cnt)} for sc, cnt in top_rows
    ]

    # 最近 10 条(不含 IP,只显示设备 + 时间,避免泄露访问者)
    latest_rows = (
        ClickLog.query.filter(*window)
        .order_by(ClickLog.clicked_at.desc(), ClickLog.id.desc())
        .limit(10)
        .all()
    )
    latest = []
    for log in latest_rows:
        parsed = analytics.parse_ua(log.user_agent)
        latest.append({
            "short_code": log.short_code,
            "device": parsed["device"],
            "browser": parsed["browser"],
            "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
        })

    return success({
        "window_minutes": minutes,
        "count": int(count),
        "top_links": top_links,
        "latest": latest,
        "server_time": _now().isoformat(),
    })


# F2.6 实时统计
# ==========================================================================

@bp.route("/api/shortlinks/<short_code>/realtime", methods=["GET"])
@auth_required
def get_realtime(short_code):
    """实时统计(PRD F2.6)

    以 click_logs 为准(跳转同步写库),因此「实时」= 直接查最近 N 分钟,
    不存在离线/在线不一致的问题。
    ---
    tags: [stats]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
      - in: query
        name: minutes
        type: integer
        default: 30
        description: 观察窗口分钟数(1-1440)
    responses:
      200: {description: 窗口内点击量 + 最近访问列表}
      401: {description: 未登录}
      404: {description: 短码不存在或无权查看}
    """
    sl = _owned_or_404(short_code)

    minutes = _int_arg(request.args.get("minutes"), default=30, lo=1, hi=1440)
    since = _now() - timedelta(minutes=minutes)

    count = (
        db.session.query(func.count())
        .select_from(ClickLog)
        .filter(ClickLog.short_code == short_code, ClickLog.clicked_at >= since)
        .scalar()
        or 0
    )
    rows = (
        ClickLog.query.filter(
            ClickLog.short_code == short_code, ClickLog.clicked_at >= since
        )
        .order_by(ClickLog.clicked_at.desc(), ClickLog.id.desc())
        .limit(20)
        .all()
    )

    items = []
    for log in rows:
        parsed = analytics.parse_ua(log.user_agent)
        items.append({
            "ip": log.ip,
            "device": parsed["device"],
            "os": parsed["os"],
            "browser": parsed["browser"],
            "referer": log.referer,
            "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
        })

    return success({
        "short_code": short_code,
        "window_minutes": minutes,
        "count": count,
        "total_pv": sl.visit_count or 0,
        "items": items,
        "server_time": _now().isoformat(),
    })


# ==========================================================================
# F2.7 导出报表
# ==========================================================================

@bp.route("/api/shortlinks/<short_code>/export", methods=["GET"])
@auth_required
def export_clicks(short_code):
    """导出点击明细 CSV(PRD F2.7)。

    直接返回 text/csv 流(不是统一 JSON 响应),前端用 blob 接收。
    超过 _EXPORT_MAX_ROWS 行时只导出最近的部分,并在响应头里给出实际行数。
    ---
    tags: [stats]
    parameters:
      - in: path
        name: short_code
        type: string
        required: true
      - in: query
        name: days
        type: integer
        default: 30
        description: 导出窗口天数(1-90)
    responses:
      200: {description: CSV 文件}
      401: {description: 未登录}
      404: {description: 短码不存在或无权查看}
    """
    _owned_or_404(short_code)

    days = _int_arg(request.args.get("days"), default=30, lo=1, hi=_MAX_WINDOW_DAYS)
    since = _now() - timedelta(days=days)

    rows = (
        ClickLog.query.filter(
            ClickLog.short_code == short_code, ClickLog.clicked_at >= since
        )
        .order_by(ClickLog.clicked_at.desc(), ClickLog.id.desc())
        .limit(_EXPORT_MAX_ROWS)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "时间(UTC)", "IP", "设备类型", "操作系统", "浏览器",
        "来源分类", "User-Agent", "Referer",
    ])
    for log in rows:
        parsed = analytics.parse_ua(log.user_agent)
        writer.writerow([
            log.clicked_at.isoformat() if log.clicked_at else "",
            log.ip or "",
            parsed["device"],
            parsed["os"],
            parsed["browser"],
            analytics.classify_referer(log.referer),
            log.user_agent or "",
            log.referer or "",
        ])

    # Excel 打开 UTF-8 CSV 需要 BOM,否则中文列头会乱码
    body = "\ufeff" + buf.getvalue()
    filename = f"shortlink-{short_code}-{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        body,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Rows": str(len(rows)),
        },
    )
