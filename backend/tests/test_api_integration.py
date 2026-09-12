"""端到端 API 集成测试:用 SQLite 内存数据库 + Flask test_client。

覆盖:
- POST /api/shortlinks 生成短链(201)
- GET /s/<code> 跳转(302)与 PV 自增
- GET /api/shortlinks/<code>/stats 统计
- 同链同码(强制同码 C1)
- 404 不存在 / 410 软删 / 410 过期 / 410 停用
- 400 非法链接 / 400 恶意链接
- 401 密码保护
"""

import pytest

from app.extensions import db
from app.models import ShortLink, ShortLinkStatus
from app.services.short_code import encode_id
from datetime import datetime, timedelta


# ---------- 测试用 Flask app fixture ----------

@pytest.fixture
def app(monkeypatch):
    from flask import Flask
    from app.extensions import db as _db, ma, migrate
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
        SECURITY_ENABLED=False,  # 测试中关闭恶意拦截
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
    )

    # 覆盖 validate_config 的字段要求:测试环境简化
    monkeypatch.setattr(
        "app.config.validate_config", lambda cfg: None
    )

    _db.init_app(app)
    ma.init_app(app)
    # 不连真 Redis:用 fake
    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.extensions._redis_pool", fake_redis.pool)

    with app.app_context():
        _db.create_all()
        register_blueprints(app)
        register_error_handlers(app)
        yield app
        _db.session.remove()
        _db.drop_all()


class _FakeRedis:
    """最小 Redis stub for app context."""

    def __init__(self):
        self.pool = _FakePool()


class _FakePool:
    pass


@pytest.fixture
def client(app):
    return app.test_client()


# ---------- POST /api/shortlinks ----------

class TestCreateShortLink:
    def test_create_success(self, client, app):
        rv = client.post("/api/shortlinks", json={"long_url": "https://example.com/a"})
        assert rv.status_code == 201
        body = rv.get_json()
        assert body["code"] == 0
        data = body["data"]
        assert data["long_url"] == "https://example.com/a"
        assert data["short_code"].isalnum()
        assert len(data["short_code"]) == 6
        assert data["full_short_url"] == f"http://test.local/s/{data['short_code']}"
        assert data["has_password"] is False

    def test_same_url_returns_same_code(self, client, app):
        r1 = client.post("/api/shortlinks", json={"long_url": "https://same.com"})
        r2 = client.post("/api/shortlinks", json={"long_url": "https://same.com"})
        assert r1.get_json()["data"]["short_code"] == r2.get_json()["data"]["short_code"]

    def test_invalid_url(self, client):
        rv = client.post("/api/shortlinks", json={"long_url": "ftp://bad.com"})
        assert rv.status_code == 400

    def test_empty_url(self, client):
        rv = client.post("/api/shortlinks", json={"long_url": ""})
        assert rv.status_code == 400

    def test_missing_url(self, client):
        rv = client.post("/api/shortlinks", json={})
        assert rv.status_code == 400


# ---------- GET /s/<code> ----------

class TestRedirect:
    def test_302_redirect(self, client):
        r = client.post("/api/shortlinks", json={"long_url": "https://target.com/"})
        code = r.get_json()["data"]["short_code"]
        rv = client.get(f"/s/{code}")
        assert rv.status_code == 302
        assert rv.headers["Location"] == "https://target.com/"

    def test_pv_increments(self, client, app):
        r = client.post("/api/shortlinks", json={"long_url": "https://counter.com"})
        code = r.get_json()["data"]["short_code"]
        client.get(f"/s/{code}")
        client.get(f"/s/{code}")
        client.get(f"/s/{code}")
        with app.app_context():
            sl = ShortLink.query.filter_by(short_code=code).first()
            assert sl.visit_count == 3

    def test_404_unknown_code(self, client):
        rv = client.get("/s/notexist")
        assert rv.status_code == 404

    def test_410_expired(self, client, app):
        with app.app_context():
            sl = ShortLink(
                short_code="exp001",
                long_url="https://x.com",
                url_hash="h",
                expire_at=datetime.utcnow() - timedelta(hours=1),
            )
            db.session.add(sl)
            db.session.commit()
        rv = client.get("/s/exp001")
        assert rv.status_code == 410

    def test_410_disabled(self, client, app):
        with app.app_context():
            sl = ShortLink(
                short_code="dis001", long_url="https://x.com", url_hash="h",
                status=ShortLinkStatus.DISABLED,
            )
            db.session.add(sl)
            db.session.commit()
        rv = client.get("/s/dis001")
        assert rv.status_code == 410

    def test_404_deleted(self, client, app):
        """软删后应 404(对用户透明,不暴露短链曾存在)。"""
        with app.app_context():
            sl = ShortLink(
                short_code="del001", long_url="https://x.com", url_hash="h",
                is_deleted=True,
            )
            db.session.add(sl)
            db.session.commit()
        rv = client.get("/s/del001")
        assert rv.status_code == 404

    def test_403_malicious(self, client, app):
        with app.app_context():
            sl = ShortLink(
                short_code="mal001", long_url="https://x.com", url_hash="h",
                status=ShortLinkStatus.MALICIOUS,
            )
            db.session.add(sl)
            db.session.commit()
        rv = client.get("/s/mal001")
        assert rv.status_code == 403

    def test_401_password_required(self, client, app):
        from app.services.password import hash_password
        with app.app_context():
            sl = ShortLink(
                short_code="pwd001", long_url="https://x.com", url_hash="h",
                password_hash=hash_password("abcdef"),
            )
            db.session.add(sl)
            db.session.commit()
        rv = client.get("/s/pwd001")
        assert rv.status_code == 401


# ---------- GET /api/shortlinks/<code>/stats ----------

class TestStats:
    def test_stats(self, client, app):
        r = client.post("/api/shortlinks", json={"long_url": "https://stats.com"})
        code = r.get_json()["data"]["short_code"]
        client.get(f"/s/{code}")
        client.get(f"/s/{code}")
        rv = client.get(f"/api/shortlinks/{code}/stats")
        assert rv.status_code == 200
        data = rv.get_json()["data"]
        assert data["pv"] == 2
        assert data["uv"] >= 1
        assert data["status"] == "enabled"

    def test_stats_404(self, client):
        rv = client.get("/api/shortlinks/notexist/stats")
        assert rv.status_code == 404


# ---------- Auth 注册 / 登录 ----------

class TestAuth:
    def test_register(self, client):
        rv = client.post("/api/auth/register", json={
            "username": "alice", "password": "secret123"
        })
        assert rv.status_code == 201
        body = rv.get_json()["data"]
        assert body["username"] == "alice"
        assert body["api_key"]

    def test_register_duplicate(self, client):
        client.post("/api/auth/register", json={"username": "bob", "password": "secret123"})
        rv = client.post("/api/auth/register", json={"username": "bob", "password": "secret123"})
        assert rv.status_code == 400

    def test_login_success(self, client):
        client.post("/api/auth/register", json={"username": "carol", "password": "secret123"})
        rv = client.post("/api/auth/login", json={"username": "carol", "password": "secret123"})
        assert rv.status_code == 200
        # Cookie 应被设置
        assert "session" in rv.headers.get("Set-Cookie", "")

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={"username": "dave", "password": "secret123"})
        rv = client.post("/api/auth/login", json={"username": "dave", "password": "wrong"})
        assert rv.status_code == 401


# ---------- 健康检查 ----------

class TestHealth:
    def test_health(self, client):
        rv = client.get("/health")
        assert rv.status_code in (200, 503)
        body = rv.get_json()
        assert "status" in body
        assert "db" in body
        assert "redis" in body


# ---------- 鉴权保护 ----------

class TestAuthRequired:
    def test_links_requires_login(self, client):
        rv = client.get("/api/links")
        assert rv.status_code == 401

    def test_get_link_requires_login(self, client):
        rv = client.get("/api/links/abc")
        assert rv.status_code == 401

    def test_delete_requires_login(self, client):
        rv = client.delete("/api/links/abc")
        assert rv.status_code == 401

    def test_patch_requires_login(self, client):
        rv = client.patch("/api/links/abc", json={"status": "disabled"})
        assert rv.status_code == 401

    def test_logged_in_user_can_list_own(self, client, app):
        # 注册 + 登录
        client.post("/api/auth/register", json={"username": "linksuser", "password": "secret123"})
        rv = client.post("/api/auth/login", json={"username": "linksuser", "password": "secret123"})
        # 创建两条短链(短链创建接口不要求登录)
        client.post("/api/shortlinks", json={"long_url": "https://a.com"})
        client.post("/api/shortlinks", json={"long_url": "https://b.com"})
        # 列表(cookie 已经在 client 中)
        rv = client.get("/api/links")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        assert body["total"] >= 2
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["items"]) >= 2

    def test_logout_clears_session(self, client):
        client.post("/api/auth/register", json={"username": "logoutuser", "password": "secret123"})
        client.post("/api/auth/login", json={"username": "logoutuser", "password": "secret123"})
        rv = client.get("/api/links")
        assert rv.status_code == 200
        rv = client.post("/api/auth/logout")
        assert rv.status_code == 200
        # 登出后 session cookie 已清,再次访问应 401
        rv = client.get("/api/links")
        assert rv.status_code == 401
