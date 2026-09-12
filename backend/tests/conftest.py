"""pytest 公共夹具与环境。

- 真依赖可用时(开发/CI)直接使用,无需任何 stub
- 缺依赖时(沙箱)为 Flask 扩展注入最小可用 stub,让纯算法层测试可跑
"""

import os
import sys
import types

# ---------- Python 路径 ----------
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)


# ---------- 缺包时注入 stub ----------
def _missing(name: str) -> bool:
    return name not in sys.modules and _import_failed(name)


def _import_failed(name: str) -> bool:
    try:
        __import__(name)
        sys.modules.pop(name, None)  # 还原,让后续正常导入
        return False
    except ImportError:
        return True


class _DummyExt:
    def __init__(self, *args, **kwargs):
        pass

    def init_app(self, app):  # noqa: ARG002
        return None


def _inject(name: str, attrs: dict) -> None:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod


if _missing("flask_sqlalchemy"):
    _inject("flask_sqlalchemy", {"SQLAlchemy": _DummyExt})
if _missing("flask_migrate"):
    _inject("flask_migrate", {"Migrate": _DummyExt})
if _missing("flask_marshmallow"):
    _inject("flask_marshmallow", {"Marshmallow": _DummyExt})
if _missing("flasgger"):
    _inject("flasgger", {"Swagger": _DummyExt})
if _missing("redis"):
    class _DummyPool:
        pass

    class _DummyRedisClient:
        pass

    _inject("redis", {
        "ConnectionPool": _DummyPool,
        "Redis": _DummyRedisClient,
        "from_url": lambda *a, **kw: _DummyRedisClient(),
    })


# ---------- 模型测试用 SQLite 内存数据库 fixture ----------
import pytest


@pytest.fixture
def sqlite_app():
    """仅在 Flask-SQLAlchemy 真实安装时可用。"""
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
    except ImportError:
        pytest.skip("Flask-SQLAlchemy 未安装,跳过 SQLite 集成测试")

    from app.extensions import db
    from app import models  # noqa: F401 触发模型注册

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sqlite_session(sqlite_app):
    from app.extensions import db

    return db.session


# ---------- API 集成测试用的完整 app(SQLite + fake Redis) ----------

class _FakePool:
    """占位连接池:让 get_redis() 能构造出客户端,但任何命令都会失败并降级。"""


@pytest.fixture
def api_app(monkeypatch):
    """带全部蓝图 + 错误处理器的 Flask app,内存 SQLite,Redis 走降级路径。"""
    from flask import Flask
    from app.extensions import db as _db, ma
    from app.api import register_blueprints
    from app.middleware.error import register_error_handlers

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="test-secret",
        BASE_DOMAIN="http://test.local",
        DB_HOST="x", DB_USER="x", DB_PASSWORD="x", DB_NAME="x",
        REDIS_HOST="127.0.0.1", REDIS_PORT=6379, REDIS_DB=15,
        RATE_LIMIT_ENABLED=False,
        SECURITY_ENABLED=False,
        LONG_URL_MAX_LENGTH=2048,
        DEFAULT_EXPIRE_DAYS=7,
        SHORT_CODE_MIN_LENGTH=6,
        SHORT_CODE_MAX_LENGTH=8,
        SHORT_CODE_AFFINE_MULTIPLIER=131,
        SHORT_CODE_AFFINE_OFFSET=577,
        SECURITY_CHECK_ON_CREATE=True,
        SECURITY_CHECK_ON_REDIRECT=True,
        SECURITY_FAIL_OPEN=False,
        PASSWORD_MIN_LENGTH=6,
        PASSWORD_MAX_LENGTH=8,
        PASSWORD_TOKEN_TTL=7200,
        PASSWORD_MAX_ATTEMPTS=10,
        ACCESS_CONTROL_ENABLED=True,
        ACCESS_CONTROL_BLOCK_STATUS=404,
    )

    monkeypatch.setattr("app.config.validate_config", lambda cfg: None)

    _db.init_app(app)
    ma.init_app(app)
    monkeypatch.setattr("app.extensions._redis_pool", _FakePool())

    with app.app_context():
        _db.create_all()
        register_blueprints(app)
        register_error_handlers(app)
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def api_client(api_app):
    return api_app.test_client()


@pytest.fixture
def logged_in_client(api_app):
    """已登录(带 session cookie)的 test client。"""
    from app.services import auth as auth_service

    auth_service.register("tester", "secret123")
    user = auth_service.get_by_username("tester")
    token = auth_service.issue_session_token(user)

    client = api_app.test_client()
    client.set_cookie("session", token)
    return client, user
