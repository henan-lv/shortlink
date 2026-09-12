"""鉴权业务(注册、登录、登出、当前用户、用户管理)。"""

import secrets
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..middleware.error import BadRequestError, ForbiddenError, NotFoundError, UnauthorizedError
from ..models import User
from . import password as password_service


def register(username: str, password: str) -> User:
    """注册新用户。首个注册的用户自动获得管理员权限,用于闭环登录页面的注册流程。"""
    if not username or len(username) < 3:
        raise BadRequestError("用户名长度至少 3")
    if not password or len(password) < 6:
        raise BadRequestError("密码长度至少 6")

    if User.query.filter_by(username=username).first():
        raise BadRequestError("用户名已存在")

    # 首位用户自动成为管理员
    is_first = db.session.query(User.id).first() is None

    user = User(
        username=username,
        password_hash=password_service.hash_password(password),
        api_key=secrets.token_urlsafe(24),
        is_admin=is_first,
        is_active=True,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BadRequestError("用户名已存在")
    return user


def login(username: str, password: str) -> User:
    user = User.query.filter_by(username=username).first()
    if not user:
        raise UnauthorizedError("用户名或密码错误")
    if not password_service.verify_password(password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    if not user.is_active:
        raise UnauthorizedError("账号已被停用,请联系管理员")
    return user


def issue_session_token(user: User) -> str:
    """签发会话 Token(Cookie 形式)。"""
    cfg = current_app.config
    ttl = cfg.get("SESSION_TOKEN_TTL", 7 * 24 * 3600)
    return password_service.issue_token(
        short_code=f"user:{user.id}:{user.username}",
        ttl=ttl,
        secret=cfg["SECRET_KEY"],
    )


def verify_session_token(token: str, user: User) -> bool:
    cfg = current_app.config
    return password_service.verify_token(
        token,
        short_code=f"user:{user.id}:{user.username}",
        secret=cfg["SECRET_KEY"],
    )


def get_by_id(user_id: int) -> User | None:
    return User.query.get(user_id)


def get_by_username(username: str) -> User | None:
    return User.query.filter_by(username=username).first()

# === 用户管理(管理员) ===

def list_users() -> list[User]:
    return User.query.order_by(User.created_at.desc()).all()


def admin_create_user(username: str, password: str, is_admin: bool = False) -> User:
    if User.query.filter_by(username=username).first():
        raise BadRequestError("用户名已存在")
    user = User(
        username=username,
        password_hash=password_service.hash_password(password),
        api_key=secrets.token_urlsafe(24),
        is_admin=is_admin,
        is_active=True,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BadRequestError("用户名已存在")
    return user


def admin_update_user(user_id: int, *, is_active=None, is_admin=None, password=None) -> User:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    if is_active is not None:
        user.is_active = bool(is_active)
    if is_admin is not None:
        # 防止最后一个管理员被降级,导致系统无主
        if user.is_admin and not is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                raise ForbiddenError("系统至少保留一名管理员")
        user.is_admin = bool(is_admin)
    if password:
        user.password_hash = password_service.hash_password(password)
    db.session.commit()
    return user


def admin_delete_user(user_id: int) -> None:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            raise ForbiddenError("系统至少保留一名管理员,无法删除")
    db.session.delete(user)
    db.session.commit()


def regenerate_api_key(user_id: int) -> User:
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    user.api_key = secrets.token_urlsafe(24)
    db.session.commit()
    return user
