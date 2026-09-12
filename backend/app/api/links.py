"""链接管理 API(列表/详情/删除/启停)。"""

from flask import Blueprint, current_app, g, request

from ..middleware.error import NotFoundError, UnauthorizedError
from ..schemas.short_link import ShortLinkListQuery, UpdateShortLinkRequest
from ..middleware.auth import auth_required
from ..services import auth as auth_service
from ..services import short_link as svc
from ..utils.response import success

bp = Blueprint("links", __name__)


def _current_user():
    """从 g 中取当前用户(由 auth_required 注入)。"""
    user = getattr(g, "current_user", None)
    if not user:
        raise UnauthorizedError("需要登录")
    return user


@bp.route("/api/links", methods=["GET"])
@auth_required
def list_links():
    """我的链接列表(分页 + 筛选 + 排序)。"""
    user = _current_user()
    params = ShortLinkListQuery().load(request.args)
    items, total = svc.list_for_user(
        user.id,
        page=params["page"],
        page_size=params["page_size"],
        include_deleted=params["include_deleted"],
        only_deleted=params["only_deleted"],
        status=params.get("status"),
        keyword=params.get("keyword"),
        channel=params.get("channel"),
        domain=params.get("domain"),
        sort=params.get("sort"),
    )
    cfg = current_app.config
    return success({
        "total": total,
        "page": params["page"],
        "page_size": params["page_size"],
        "items": [_serialize(sl, cfg) for sl in items],
    })


@bp.route("/api/links/<short_code>", methods=["GET"])
@auth_required
def get_link(short_code):
    user = _current_user()
    sl = svc.get_by_code(short_code)
    if sl is None or sl.user_id != user.id:
        raise NotFoundError("链接不存在")
    return success(_serialize(sl, current_app.config))


@bp.route("/api/links/<short_code>", methods=["DELETE"])
@auth_required
def delete_link(short_code):
    """软删除链接(进入回收站,可通过 restore 撤销)。"""
    user = _current_user()
    sl = svc.get_by_code(short_code)
    if sl is None or sl.user_id != user.id:
        raise NotFoundError("链接不存在")
    svc.soft_delete(sl)
    return success({"short_code": short_code, "is_deleted": True})


@bp.route("/api/links/<short_code>/restore", methods=["POST"])
@auth_required
def restore_link(short_code):
    """恢复已软删的链接(撤销误删)。"""
    user = _current_user()
    sl = svc.get_by_code(short_code)
    if sl is None or sl.user_id != user.id:
        raise NotFoundError("链接不存在")
    svc.restore(sl)
    return success(_serialize(sl, current_app.config))


@bp.route("/api/links/<short_code>", methods=["PATCH"])
@auth_required
def patch_link(short_code):
    user = _current_user()
    payload = UpdateShortLinkRequest().load(request.get_json(silent=True) or {})
    sl = svc.get_by_code(short_code)
    if sl is None or sl.user_id != user.id:
        raise NotFoundError("链接不存在")
    svc.update_status(sl, payload["status"])
    return success({"short_code": short_code, "status": sl.status})


def _serialize(sl, cfg) -> dict:
    base = (sl.domain or cfg.get("BASE_DOMAIN") or (request.scheme + "://" + request.host)).rstrip("/")
    return {
        "id": sl.id,
        "short_code": sl.short_code,
        "long_url": sl.long_url,
        "full_short_url": f"{base}/s/{sl.short_code}",
        "status": sl.status,
        "has_password": bool(sl.password_hash),
        "is_deleted": bool(sl.is_deleted),
        "deleted_at": sl.deleted_at.isoformat() if sl.deleted_at else None,
        "pv": sl.visit_count,
        "uv": svc.get_uv(sl),
        "click_limit": sl.click_limit,
        "effective_at": sl.effective_at.isoformat() if sl.effective_at else None,
        "created_at": sl.created_at.isoformat() if sl.created_at else None,
        "expire_at": sl.expire_at.isoformat() if sl.expire_at else None,
        "last_visit_at": sl.last_visit_at.isoformat() if sl.last_visit_at else None,
        "domain": sl.domain,
        "channel": sl.channel,
    }
