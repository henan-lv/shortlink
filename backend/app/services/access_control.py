"""访问控制 / 风控服务。

职责:
  1. parse_advanced()  把生成页「高级设置」JSON 解析成规则草稿
  2. load_rules()      加载某条短链生效的规则(global + short_code),带 Redis 版本号缓存
  3. evaluate()        对一次访问做判定(白名单优先 → 黑名单命中)
  4. record_hit()      记录拦截 / 观察计数(Redis,避免刷爆 click_logs)
  5. get_hit_stats()   读取拦截计数,供统计页展示

高级设置 schema(生成页「高级设置」应产出这个结构):
    {
      "access_control": {
        "block_ips":     ["1.2.3.4", "10.0.0.0/8"],
        "block_ua":      ["bot", "spider"],
        "block_referer": ["spam.example"],
        "allow_ips":     ["203.0.113.0/24"],
        "action":        "block"          // block | observe
      }
    }

语义:
  - 只要配置了 allow_ips(白名单),未命中白名单的访问一律拒绝;
  - block_* 命中后按 action 处置:block=拒绝,observe=只计数放行;
  - 全部为空 → 不做任何拦截。

缓存:
  规则读多写少且在跳转热路径上,用 Redis 做缓存。
  写入规则后 bump_version() 递增版本号,旧缓存键自然失效(无需扫描删除)。
  Redis 不可用时自动回退到直接查库。
"""

import ipaddress
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from flask import current_app
from sqlalchemy import and_, or_

from ..extensions import db, get_redis
from ..middleware.error import BadRequestError
from ..models import AccessRule, AccessRuleAction, AccessRuleMode, AccessRuleScope, AccessRuleSource

logger = logging.getLogger(__name__)

# 单条短链最多允许的规则数,防止配置爆炸
MAX_RULES_PER_LINK = 100

_RULE_CACHE_TTL = 60          # 规则缓存秒数
# 拦截计数保留天数。必须 >= 统计接口允许查询的最大窗口(_MAX_WINDOW_DAYS = 90),
# 否则用户选「近 30 天」时「已拦截」会偏小甚至为 0,看起来像 bug。
_HIT_COUNTER_TTL = 90 * 86400

_net_cache: dict[str, object] = {}


# ---------- 高级设置解析 ----------

@dataclass
class RuleSpec:
    """规则草稿,尚未落库。"""
    rule_type: str
    value: str
    mode: str = AccessRuleMode.BLOCK
    action: str = AccessRuleAction.BLOCK


def _as_list(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        # 允许逗号 / 换行分隔的字符串写法
        raw = val.replace("\n", ",").replace(";", ",")
        return [x.strip() for x in raw.split(",") if x.strip()]
    if isinstance(val, (list, tuple, set)):
        return [str(x).strip() for x in val if str(x).strip()]
    return []


def _norm_ip(value: str) -> RuleSpec:
    """IP 或 CIDR → RuleSpec(自动判别类型)。非法输入抛 400。"""
    v = value.strip()
    if "/" in v:
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError as exc:
            raise BadRequestError(f"非法的 CIDR 网段:{v}") from exc
        return RuleSpec(rule_type="ip_cidr", value=v)
    try:
        ipaddress.ip_address(v)
    except ValueError as exc:
        raise BadRequestError(f"非法的 IP 地址:{v}") from exc
    return RuleSpec(rule_type="ip", value=v)


def parse_advanced(advanced) -> list[RuleSpec]:
    """把高级设置 JSON 解析成规则草稿列表。

    兼容两种写法:嵌套 {"access_control": {...}} 与扁平 {...}。
    非法 IP/CIDR 抛 BadRequestError;其他字段宽松处理。
    """
    if not isinstance(advanced, dict):
        return []
    ac = advanced.get("access_control")
    if ac is None:
        ac = advanced
    if not isinstance(ac, dict):
        return []

    action = str(ac.get("action") or AccessRuleAction.BLOCK).strip().lower()
    if action not in AccessRuleAction.ALL:
        action = AccessRuleAction.BLOCK

    specs: list[RuleSpec] = []

    for raw in _as_list(ac.get("allow_ips")):
        spec = _norm_ip(raw)
        spec.mode = AccessRuleMode.ALLOW
        specs.append(spec)

    for raw in _as_list(ac.get("block_ips")):
        spec = _norm_ip(raw)
        spec.mode = AccessRuleMode.BLOCK
        spec.action = action
        specs.append(spec)

    for kw in _as_list(ac.get("block_ua")):
        specs.append(RuleSpec("ua", kw[:255], AccessRuleMode.BLOCK, action))

    for kw in _as_list(ac.get("block_referer")):
        specs.append(RuleSpec("referer", kw[:255], AccessRuleMode.BLOCK, action))

    # 去重(同 type+value+mode)
    seen = set()
    unique: list[RuleSpec] = []
    for s in specs:
        key = (s.rule_type, s.value.lower(), s.mode)
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    if len(unique) > MAX_RULES_PER_LINK:
        raise BadRequestError(f"风控规则过多,单条链接最多 {MAX_RULES_PER_LINK} 条")

    return unique


def sync_advanced_rules(sl, advanced, user_id: Optional[int]) -> int:
    """用高级设置覆盖该短链由高级设置产生的规则(幂等,不 commit)。

    只清理 source=advanced 的旧规则,不动统计页手动创建的规则。
    返回本次写入的规则条数。
    """
    specs = parse_advanced(advanced)
    AccessRule.query.filter_by(
        short_code=sl.short_code, source=AccessRuleSource.ADVANCED
    ).delete(synchronize_session=False)
    for s in specs:
        db.session.add(AccessRule(
            user_id=user_id,
            rule_type=s.rule_type,
            value=s.value,
            mode=s.mode,
            action=s.action,
            scope=AccessRuleScope.SHORT_CODE,
            short_code=sl.short_code,
            source=AccessRuleSource.ADVANCED,
            reason="生成页高级设置",
            enabled=True,
        ))
    return len(specs)


# ---------- 规则加载(带缓存) ----------

def _redis_or_none():
    try:
        return get_redis()
    except Exception:  # noqa: BLE001 - Redis 不可用时降级
        return None


def _version_key(user_id) -> str:
    return f"sl:acrver:{user_id}"


def bump_version(user_id) -> None:
    """规则变更后调用:递增版本号,让该用户所有短链的规则缓存立即失效。"""
    if user_id is None:
        return
    r = _redis_or_none()
    if r is None:
        return
    try:
        r.incr(_version_key(user_id))
    except Exception:  # noqa: BLE001
        logger.debug("bump access-rule version failed", exc_info=True)


def _get_version(user_id) -> Optional[str]:
    r = _redis_or_none()
    if r is None:
        return None
    try:
        v = r.get(_version_key(user_id))
        if v is None:
            return "0"
        return v.decode() if isinstance(v, bytes) else str(v)
    except Exception:  # noqa: BLE001
        return None


def _query_rules(short_code: str, owner_id: Optional[int]) -> list[AccessRule]:
    """从库中取该短链生效的规则:global(限本用户名下) + short_code。"""
    conds = [
        and_(
            AccessRule.scope == AccessRuleScope.SHORT_CODE,
            AccessRule.short_code == short_code,
        )
    ]
    if owner_id is not None:
        conds.append(and_(
            AccessRule.scope == AccessRuleScope.GLOBAL,
            AccessRule.user_id == owner_id,
        ))
    rows = (
        AccessRule.query
        .filter(AccessRule.enabled.is_(True))
        .filter(or_(*conds))
        .all()
    )
    return [r for r in rows if not r.is_expired()]


def query_active_rules(short_code: str, owner_id: Optional[int]) -> list[AccessRule]:
    """直接查库返回生效规则(带 id,供管理接口/统计页展示)。"""
    return _query_rules(short_code, owner_id)


def load_rules(short_code: str, owner_id: Optional[int] = None) -> list[AccessRule]:
    """加载短链生效规则(带 Redis 版本号缓存),用于跳转热路径判定。"""
    version = _get_version(owner_id) if owner_id is not None else None
    cache_key = f"sl:acr:{owner_id}:{version}:{short_code}"

    if version is not None:
        r = _redis_or_none()
        if r is not None:
            try:
                raw = r.get(cache_key)
                if raw:
                    return _deserialize(raw)
            except Exception:  # noqa: BLE001
                pass

    rules = _query_rules(short_code, owner_id)

    if version is not None:
        r = _redis_or_none()
        if r is not None:
            try:
                r.setex(cache_key, _RULE_CACHE_TTL, _serialize(rules))
            except Exception:  # noqa: BLE001
                pass
    return rules


def _serialize(rules: Iterable[AccessRule]) -> str:
    return json.dumps([
        {"t": r.rule_type, "v": r.value, "m": r.mode, "a": r.action}
        for r in rules
    ], ensure_ascii=False)


def _deserialize(raw) -> list[AccessRule]:
    """缓存反序列化成轻量对象(只带匹配需要的字段,不挂 session)。"""
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        items = json.loads(raw)
    except (ValueError, TypeError):
        return []
    out = []
    for it in items:
        rule = AccessRule(
            rule_type=it.get("t"), value=it.get("v"),
            mode=it.get("m"), action=it.get("a"),
        )
        # 标记为游离对象,避免被 session 误当成待插入记录
        from sqlalchemy.orm import make_transient
        make_transient(rule)
        out.append(rule)
    return out


# ---------- 判定 ----------

@dataclass
class AccessDecision:
    blocked: bool = False
    observed: bool = False
    reason: str = ""
    rule: Optional[AccessRule] = field(default=None, repr=False)


def _ip_in_cidr(ip: str, cidr: str) -> bool:
    net = _net_cache.get(cidr)
    if net is None:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return False
        _net_cache[cidr] = net
    try:
        return ipaddress.ip_address(ip) in net  # type: ignore[operator]
    except (ValueError, TypeError):
        # ValueError: 非法 IP;TypeError: v4 与 v6 网段比较
        return False


def match_rule(rule: AccessRule, ip: Optional[str], ua: Optional[str], referer: Optional[str]) -> bool:
    """单条规则是否命中当前访问者。"""
    rt = rule.rule_type
    val = (rule.value or "").strip()
    if not val:
        return False
    if rt == "ip":
        return bool(ip) and ip == val
    if rt == "ip_cidr":
        return bool(ip) and _ip_in_cidr(ip, val)
    if rt == "ua":
        return bool(ua) and val.lower() in ua.lower()
    if rt == "referer":
        return bool(referer) and val.lower() in referer.lower()
    return False


def evaluate(
    rules: Iterable[AccessRule],
    ip: Optional[str] = None,
    ua: Optional[str] = None,
    referer: Optional[str] = None,
) -> AccessDecision:
    """判定一次访问。

    顺序:
      1. 白名单:存在 allow 规则且未命中 → 拒绝
      2. 黑名单:命中 block 规则 → 按 action 处置
      3. 否则放行
    """
    rules = list(rules)
    allow_rules = [r for r in rules if r.mode == AccessRuleMode.ALLOW]
    block_rules = [r for r in rules if r.mode == AccessRuleMode.BLOCK]

    if allow_rules and not any(match_rule(r, ip, ua, referer) for r in allow_rules):
        return AccessDecision(blocked=True, reason="whitelist_miss")

    for r in block_rules:
        if match_rule(r, ip, ua, referer):
            if r.action == AccessRuleAction.OBSERVE:
                return AccessDecision(observed=True, reason="observed", rule=r)
            return AccessDecision(blocked=True, reason="blocked", rule=r)

    return AccessDecision()


def has_allow_rules(rules: Iterable[AccessRule]) -> bool:
    return any(r.mode == AccessRuleMode.ALLOW for r in rules)


def find_matching_rule(
    rules: Iterable[AccessRule],
    ip: Optional[str] = None,
    ua: Optional[str] = None,
    referer: Optional[str] = None,
) -> Optional[AccessRule]:
    for r in rules:
        if r.mode == AccessRuleMode.BLOCK and match_rule(r, ip, ua, referer):
            return r
    return None


# ---------- 拦截计数(Redis) ----------

def _day(offset: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=offset)).strftime("%Y%m%d")


def record_hit(short_code: str, ip: Optional[str], observed: bool = False) -> None:
    """记录一次拦截/观察。被拦的请求不写 click_logs,靠这里保留计数。"""
    r = _redis_or_none()
    if r is None:
        return
    try:
        d = _day()
        if observed:
            k = f"sl:obs:{short_code}:{d}"
            r.incr(k)
            r.expire(k, _HIT_COUNTER_TTL)
            return
        k = f"sl:blk:{short_code}:{d}"
        r.incr(k)
        r.expire(k, _HIT_COUNTER_TTL)
        hk = f"sl:blkip:{short_code}:{d}"
        r.hincrby(hk, ip or "-", 1)
        r.expire(hk, _HIT_COUNTER_TTL)
    except Exception:  # noqa: BLE001
        logger.debug("record access-control hit failed", exc_info=True)


def _to_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def get_hit_stats(short_code: str, days: int = 1) -> dict:
    """读取近 N 天的拦截 / 观察计数与拦截 IP Top。

    N 的上限与 _HIT_COUNTER_TTL 对齐(90 天),保证「查得到的窗口」
    一定有对应计数,不会出现窗口比保留期还长的空档。
    """
    out = {"blocked": 0, "observed": 0, "top_ips": [], "retention_days": _HIT_COUNTER_TTL // 86400}
    r = _redis_or_none()
    if r is None:
        return out
    days = max(1, min(int(days or 1), _HIT_COUNTER_TTL // 86400))
    try:
        ip_counts: dict[str, int] = {}
        for i in range(days):
            d = _day(-i)
            out["blocked"] += _to_int(r.get(f"sl:blk:{short_code}:{d}"))
            out["observed"] += _to_int(r.get(f"sl:obs:{short_code}:{d}"))
            h = r.hgetall(f"sl:blkip:{short_code}:{d}") or {}
            for k, v in h.items():
                kk = k.decode() if isinstance(k, bytes) else str(k)
                ip_counts[kk] = ip_counts.get(kk, 0) + _to_int(v)
        out["top_ips"] = [
            {"ip": k, "count": v}
            for k, v in sorted(ip_counts.items(), key=lambda x: -x[1])[:10]
        ]
    except Exception:  # noqa: BLE001
        logger.debug("read access-control stats failed", exc_info=True)
    return out


def get_user_blocked_totals(short_codes, days: int = 7) -> dict:
    """批量取多条短码在窗口内的拦截次数。

    总览页要算「全站拦截数」「Top 拦截链接」时用。返回 {short_code: count}。
    Redis 不可用或短码为空时返回 {}。days 受 _HIT_COUNTER_TTL 上限保护,
    与单链 get_hit_stats 行为一致。
    """
    out: dict[str, int] = {}
    if not short_codes:
        return out
    r = _redis_or_none()
    if r is None:
        return out
    days = max(1, min(int(days or 1), _HIT_COUNTER_TTL // 86400))
    try:
        # 同一天 key 被多条短码共用,所以用 mget 一次性拉所有 (code, day)
        # key 减少 RTT。但 day 数量随窗口变,这里改用 pipeline 更稳。
        pipe = r.pipeline(transaction=False)
        keys_per_code = [[f"sl:blk:{c}:{_day(-i)}" for i in range(days)] for c in short_codes]
        for keys in keys_per_code:
            pipe.mget(keys)
        results = pipe.execute()
        for code, vals in zip(short_codes, results):
            total = 0
            for v in (vals or []):
                if v is None:
                    continue
                total += _to_int(v)
            if total:
                out[code] = total
    except Exception:  # noqa: BLE001
        logger.debug("read user blocked totals failed", exc_info=True)
    return out


# ---------- 供 API 复用的小工具 ----------

def parse_ttl_hours(raw) -> Optional[datetime]:
    """把「封禁时长(小时)」转成 expire_at(naive UTC)。None/0 表示永久。"""
    if raw in (None, "", 0, "0"):
        return None
    try:
        hours = float(raw)
    except (TypeError, ValueError):
        raise BadRequestError("封禁时长不合法")
    if hours <= 0:
        return None
    if hours > 24 * 365:
        raise BadRequestError("封禁时长过长")
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)


def access_control_enabled() -> bool:
    try:
        return bool(current_app.config.get("ACCESS_CONTROL_ENABLED", True))
    except RuntimeError:
        return True
