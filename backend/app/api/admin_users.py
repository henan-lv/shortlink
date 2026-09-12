"""管理员 · 用户管理 API。"""

from flask import Blueprint, g, request

from ..middleware.auth import admin_required
from ..middleware.error import BadRequestError
from ..schemas.user import AdminCreateUserRequest, AdminUpdateUserRequest
from ..services import auth as auth_service
from ..utils.response import success


bp = Blueprint("admin_users", __name__)


def _serialize(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "api_key": user.api_key,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@bp.route("/api/admin/users", methods=["GET"])
def list_users():
    """列出全部用户(管理员视角)。"""
    @admin_required
    def _inner():
        items = [_serialize(u) for u in auth_service.list_users()]
        return success({"items": items, "total": len(items)})
    return _inner()


@bp.route("/api/admin/users", methods=["POST"])
def create_user():
    """管理员直接创建账号(也可用于替换公开注册)。"""
    @admin_required
    def _inner():
        payload = AdminCreateUserRequest().load(request.get_json(silent=True) or {})
        user = auth_service.admin_create_user(
            payload["username"],
            payload["password"],
            bool(payload.get("is_admin")),
        )
        return success(_serialize(user), http_status=201)
    return _inner()


@bp.route("/api/admin/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id: int):
    """更新用户:启用/停用、提权/降权、重置密码。"""
    @admin_required
    def _inner():
        payload = AdminUpdateUserRequest().load(request.get_json(silent=True) or {})
        user = auth_service.admin_update_user(
            user_id,
            is_active=payload.get("is_active"),
            is_admin=payload.get("is_admin"),
            password=payload.get("password"),
        )
        return success(_serialize(user))
    return _inner()


@bp.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    """删除用户。"""
    @admin_required
    def _inner():
        # 不允许自删
        if g.current_user and g.current_user.id == user_id:
            raise BadRequestError("不能删除自己的账号")
        auth_service.admin_delete_user(user_id)
        return success({"message": "已删除"})
    return _inner()


@bp.route("/api/admin/users/<int:user_id>/regenerate-key", methods=["POST"])
def regenerate_key(user_id: int):
    """重置 API Key。"""
    @admin_required
    def _inner():
        user = auth_service.regenerate_api_key(user_id)
        return success(_serialize(user))
    return _inner()
