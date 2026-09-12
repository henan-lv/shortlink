"""访问控制规则 API(统计页「一键拦截」与规则管理)。

  - GET    /api/access-rules            列出当前用户的风控规则
  - POST   /api/access-rules            新建规则(一键拦截 / 全局封禁)
  - PATCH  /api/access-rules/<id>       启用 / 停用
  - DELETE /api/access-rules/<id>       删除(解封)

写操作后都会 bump Redis 版本号,让跳转链路的新规则立即生效。
"""

import ipaddress

from flask import Blueprint, g, request

from ..extensions import db
from ..middleware.auth import auth_required
from ..middleware.error import BadRequestError, NotFoundError
from ..models import (
    AccessRule,
    AccessRuleAction,
    AccessRuleMode,
    AccessRuleScope,
    AccessRuleSource,
    AccessRuleType,
    ShortLink,
)
from ..services import access_control
from ..utils.response import success

bp = Blueprint("access_rules", __name__)


def _current_user():
    user = getattr(g, "current_user", None)
    if user is None:
        raise NotFoundError("未登录")
    return user


def _infer_rule_type(value: str) -> str:
    """未显式给 rule_type 时,按值的形态推断。"""
    v = (value or "").strip()
    if "/" in v:
        try:
            ipaddress.ip_network(v, strict=False)
            return AccessRuleType.IP_CIDR
        except ValueError as exc:
            raise BadRequestError(f"非法的 CIDR 网段:{v}") from exc
    try:
        ipaddress.ip_address(v)
        return AccessRuleType.IP
    except ValueError as exc:
        raise BadRequestError("无法识别规则类型,请显式传 rule_type") from exc


@bp.route("/api/access-rules", methods=["GET"])
@auth_required
def list_rules():
    """列出当前用户的风控规则
    ---
    tags: [access-rules]
    parameters:
      - in: query
        name: short_code
        type: string
        description: 只看某条短链的规则
      - in: query
        name: scope
        type: string
        enum: [short_code, global]
      - in: query
        name: include_expired
        type: boolean
        default: false
    responses:
      200: {description: 规则列表}
      401: {description: 未登录}
    """
    user = _current_user()
    q = AccessRule.query.filter_by(user_id=user.id)

    short_code = request.args.get("short_code")
    if short_code:
        q = q.filter_by(short_code=short_code)
    scope = request.args.get("scope")
    if scope:
        if scope not in AccessRuleScope.ALL:
            raise BadRequestError("scope 仅支持 short_code / global")
        q = q.filter_by(scope=scope)

    rows = q.order_by(AccessRule.id.desc()).all()
    include_expired = _bool_arg(request.args.get("include_expired"))
    if not include_expired:
        rows = [r for r in rows if not r.is_expired()]

    return success({"total": len(rows), "items": [r.to_dict() for r in rows]})


@bp.route("/api/access-rules", methods=["POST"])
@auth_required
def create_rule():
    """新建访问控制规则(统计页一键拦截)
    ---
    tags: [access-rules]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [value]
          properties:
            value: {type: string, description: "IP / CIDR / UA 关键词 / Referer 关键词"}
            rule_type: {type: string, enum: [ip, ip_cidr, ua, referer], description: "缺省时按 value 形态推断"}
            mode: {type: string, enum: [block, allow], default: block}
            action: {type: string, enum: [block, observe], default: block}
            scope: {type: string, enum: [short_code, global], default: short_code}
            short_code: {type: string, description: "scope=short_code 时必填"}
            ttl_hours: {type: number, description: "封禁时长(小时),留空为永久"}
            reason: {type: string}
    responses:
      201: {description: 创建成功}
      400: {description: 参数错误}
      404: {description: 短码不存在或无权操作}
    """
    user = _current_user()
    body = request.get_json(silent=True) or {}

    raw_value = body.get("value")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise BadRequestError("value 不能为空")
    value = raw_value.strip()[:255]

    rule_type = (body.get("rule_type") or "").strip().lower() or _infer_rule_type(value)
    if rule_type not in AccessRuleType.ALL:
        raise BadRequestError("rule_type 仅支持 ip / ip_cidr / ua / referer")

    mode = (body.get("mode") or AccessRuleMode.BLOCK).strip().lower()
    if mode not in AccessRuleMode.ALL:
        raise BadRequestError("mode 仅支持 block / allow")

    action = (body.get("action") or AccessRuleAction.BLOCK).strip().lower()
    if action not in AccessRuleAction.ALL:
        raise BadRequestError("action 仅支持 block / observe")

    scope = (body.get("scope") or AccessRuleScope.SHORT_CODE).strip().lower()
    if scope not in AccessRuleScope.ALL:
        raise BadRequestError("scope 仅支持 short_code / global")

    short_code = None
    if scope == AccessRuleScope.SHORT_CODE:
        short_code = (body.get("short_code") or "").strip()
        if not short_code:
            raise BadRequestError("scope=short_code 时必须提供 short_code")
        sl = ShortLink.query.filter_by(short_code=short_code, is_deleted=False).first()
        if sl is None or sl.user_id != user.id:
            raise NotFoundError("短码不存在")

    reason = (body.get("reason") or "").strip()[:255] or None
    expire_at = access_control.parse_ttl_hours(body.get("ttl_hours"))

    # 幂等:同维度同值同模式的生效规则已存在则直接复用,避免重复堆叠
    existing = (
        AccessRule.query
        .filter_by(
            user_id=user.id,
            rule_type=rule_type,
            value=value,
            mode=mode,
            scope=scope,
            short_code=short_code,
            enabled=True,
        )
        .all()
    )
    for r in existing:
        if not r.is_expired():
            return success(r.to_dict(), http_status=201)

    rule = AccessRule(
        user_id=user.id,
        rule_type=rule_type,
        value=value,
        mode=mode,
        action=action,
        scope=scope,
        short_code=short_code,
        reason=reason,
        source=AccessRuleSource.MANUAL,
        enabled=True,
        expire_at=expire_at,
    )
    db.session.add(rule)
    db.session.commit()
    access_control.bump_version(user.id)
    return success(rule.to_dict(), http_status=201)


@bp.route("/api/access-rules/<int:rule_id>", methods=["PATCH"])
@auth_required
def update_rule(rule_id):
    """启用 / 停用规则

    请求体 {"enabled": true|false}。
    """
    user = _current_user()
    rule = _get_owned(user, rule_id)
    body = request.get_json(silent=True) or {}
    if "enabled" not in body:
        raise BadRequestError("缺少 enabled 字段")
    rule.enabled = bool(body.get("enabled"))
    db.session.commit()
    access_control.bump_version(user.id)
    return success(rule.to_dict())


@bp.route("/api/access-rules/<int:rule_id>", methods=["DELETE"])
@auth_required
def delete_rule(rule_id):
    """删除规则(解封)。"""
    user = _current_user()
    rule = _get_owned(user, rule_id)
    db.session.delete(rule)
    db.session.commit()
    access_control.bump_version(user.id)
    return success({"id": rule_id, "deleted": True})


def _get_owned(user, rule_id: int) -> AccessRule:
    rule = AccessRule.query.filter_by(id=rule_id, user_id=user.id).first()
    if rule is None:
        raise NotFoundError("规则不存在")
    return rule


def _bool_arg(raw) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")
