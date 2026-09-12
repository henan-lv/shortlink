"""鉴权装饰器:从 session cookie 解析当前用户。"""

from functools import wraps

from flask import g, request

from ..middleware.error import UnauthorizedError
from ..services import auth as auth_service


def auth_required(view):
    """要求请求带有有效 session,否则抛 401。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("session") or _bearer_token(request)
        user = _resolve_user(token)
        if user is None:
            raise UnauthorizedError("未登录或会话已过期")
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


def auth_optional(view):
    """如有 session 则注入用户,无则不报错(用于可选登录的接口)。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("session") or _bearer_token(request)
        g.current_user = _resolve_user(token)
        return view(*args, **kwargs)

    return wrapper


def _bearer_token(req) -> str | None:
    auth = req.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def _resolve_user(token: str | None):
    if not token:
        return None
    # token 格式:user:{id}:{username}|{expires}|{sig}
    try:
        prefix, _, _ = token.partition("|")
        _, uid_str, _username = prefix.split(":", 2)
        uid = int(uid_str)
    except (ValueError, AttributeError):
        return None
    user = auth_service.get_by_id(uid)
    if user is None:
        return None
    if not auth_service.verify_session_token(token, user):
        return None
    return user

def admin_required(view):
    """要求请求为已登录的管理员账号,否则 403。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("session") or _bearer_token(request)
        user = _resolve_user(token)
        if user is None:
            raise UnauthorizedError("未登录或会话已过期")
        if not user.is_admin:
            from ..middleware.error import ForbiddenError
            raise ForbiddenError("需要管理员权限")
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper
