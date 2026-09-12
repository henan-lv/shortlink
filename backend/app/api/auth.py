"""鉴权 API(注册/登录/登出)。"""

from flask import Blueprint, g, make_response, request

from ..middleware.error import BadRequestError, UnauthorizedError
from ..schemas.user import LoginRequest, RegisterRequest
from ..services import auth as auth_service
from ..utils.response import success

bp = Blueprint("auth", __name__)


@bp.route("/api/auth/register", methods=["POST"])
def register():
    """注册新用户。"""
    payload = RegisterRequest().load(request.get_json(silent=True) or {})
    user = auth_service.register(payload["username"], payload["password"])
    return success({
        "id": user.id,
        "username": user.username,
        "api_key": user.api_key,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }, http_status=201)


@bp.route("/api/auth/login", methods=["POST"])
def login():
    """登录,下发会话 Cookie。"""
    payload = LoginRequest().load(request.get_json(silent=True) or {})
    user = auth_service.login(payload["username"], payload["password"])
    token = auth_service.issue_session_token(user)
    resp = make_response(success({
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "token": token,
    }))
    resp.set_cookie("session", token, httponly=True, samesite="Lax")
    return resp


@bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """登出,清除 Cookie。"""
    resp = make_response(success({"message": "已登出"}))
    resp.delete_cookie("session")
    return resp


@bp.route("/api/auth/me", methods=["GET"])
def me():
    """查询当前会话用户(无 session 时 401)。用于前端刷新后恢复登录态。"""
    from ..middleware.auth import auth_required

    @auth_required
    def _inner():
        user = g.current_user
        return success({
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
        })

    return _inner()
