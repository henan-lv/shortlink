"""用户管理 API 测试(顶部 nav · 用户 菜单对应后端)。

覆盖:
- 鉴权:未登录 401 / 普通用户 403 / 管理员 200
- GET    /api/admin/users
- POST   /api/admin/users         (可指定 is_admin)
- PATCH  /api/admin/users/<id>   (is_active / is_admin / password)
- DELETE /api/admin/users/<id>   (防自删、防最后一个 admin)
- POST   /api/admin/users/<id>/regenerate-key
"""
from __future__ import annotations

import pytest


# ==========================================================================
# Fixtures
# ==========================================================================

@pytest.fixture
def _redis(monkeypatch):
    """统一的假 Redis,避免每个 fixture 重复。"""
    class _FakeRedis:
        def ping(self): return True
        def get(self, k): return getattr(self, 'kv', {}).get(k)
        def set(self, k, v, ex=None, nx=False):
            if not hasattr(self, 'kv'): self.kv = {}
            if nx and k in self.kv: return False
            self.kv[k] = v; return True
        def setex(self, k, ttl, v):
            if not hasattr(self, 'kv'): self.kv = {}
            self.kv[k] = v; return True
        def incr(self, k):
            if not hasattr(self, 'kv'): self.kv = {}
            self.kv[k] = self.kv.get(k, 0) + 1
            return self.kv[k]
        def expire(self, k, ttl): return True
        def zincrby(self, *a, **k): return 1
        def zadd(self, *a, **k): return 1
        def zremrangebyscore(self, *a, **k): return 1
        def zcard(self, *a, **k): return 0
        def delete(self, *a, **k): return 1

    class _FakePool:
        connection_kwargs = {}
        decode_responses = True

    fake = _FakeRedis()
    monkeypatch.setattr("app.extensions._redis_pool", _FakePool())
    monkeypatch.setattr("app.extensions.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.password.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.short_link.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.health.get_redis", lambda: fake)


def _login(api_app, username, password):
    client = api_app.test_client()
    rv = client.post("/api/auth/login", json={"username": username, "password": password})
    assert rv.status_code == 200, rv.get_json()
    return client


@pytest.fixture
def admin_client(_redis, api_app):
    """管理员 admin 登录后的 test client。"""
    from app.services import auth as auth_service

    auth_service.admin_create_user("admin", "admin-secret", is_admin=True)
    auth_service.register("tester", "tester-secret")
    return _login(api_app, "admin", "admin-secret")


@pytest.fixture
def admin2_client(admin_client, api_app):
    """第二名管理员(用于"最后一个 admin"边界测试)。"""
    rv = admin_client.post("/api/admin/users", json={
        "username": "admin2", "password": "admin2-secret", "is_admin": True,
    })
    assert rv.status_code == 201
    return _login(api_app, "admin2", "admin2-secret")


@pytest.fixture
def normal_client(_redis, api_app):
    """普通登录用户。"""
    from app.services import auth as auth_service

    auth_service.admin_create_user("admin3", "admin3-secret", is_admin=True)
    auth_service.register("tester", "tester-secret")
    return _login(api_app, "tester", "tester-secret")


def _user_id(api_app, username):
    from app.models import User
    with api_app.app_context():
        u = User.query.filter_by(username=username).first()
        return u.id


# ==========================================================================
# 鉴权(admin_required)
# ==========================================================================

class TestAuthGuard:
    def test_unauthenticated_returns_401(self, api_client):
        for method, url, body in [
            ("GET", "/api/admin/users", None),
            ("POST", "/api/admin/users", {"username": "x1", "password": "x123456"}),
            ("PATCH", "/api/admin/users/1", {"is_active": False}),
            ("DELETE", "/api/admin/users/1", None),
            ("POST", "/api/admin/users/1/regenerate-key", None),
        ]:
            if method == "GET":
                rv = api_client.get(url)
            elif method == "POST":
                rv = api_client.post(url, json=body)
            elif method == "PATCH":
                rv = api_client.patch(url, json=body)
            elif method == "DELETE":
                rv = api_client.delete(url)
            assert rv.status_code == 401, f"{method} {url} should 401, got {rv.status_code}"

    def test_non_admin_returns_403(self, normal_client):
        rv = normal_client.get("/api/admin/users")
        assert rv.status_code == 403
        assert rv.get_json()["code"] == 403


# ==========================================================================
# GET /api/admin/users
# ==========================================================================

class TestListUsers:
    def test_list_returns_all_users(self, admin_client):
        rv = admin_client.get("/api/admin/users")
        assert rv.status_code == 200
        data = rv.get_json()["data"]
        assert data["total"] >= 2
        usernames = {u["username"] for u in data["items"]}
        assert {"admin", "tester"}.issubset(usernames)

        for u in data["items"]:
            for k in ("id", "username", "api_key", "is_admin", "is_active", "created_at"):
                assert k in u


# ==========================================================================
# POST /api/admin/users
# ==========================================================================

class TestCreateUser:
    def test_create_normal_user_201(self, admin_client):
        rv = admin_client.post("/api/admin/users", json={
            "username": "alice", "password": "alice123",
        })
        assert rv.status_code == 201
        d = rv.get_json()["data"]
        assert d["username"] == "alice"
        assert d["is_admin"] is False
        assert d["is_active"] is True
        assert d["api_key"]

    def test_create_admin_user(self, admin_client):
        rv = admin_client.post("/api/admin/users", json={
            "username": "root2", "password": "root2pw", "is_admin": True,
        })
        assert rv.status_code == 201
        assert rv.get_json()["data"]["is_admin"] is True

    def test_create_duplicate_username_returns_400(self, admin_client):
        rv = admin_client.post("/api/admin/users", json={
            "username": "tester", "password": "whatever1",
        })
        assert rv.status_code == 400
        assert "已存在" in rv.get_json()["message"]

    def test_create_validation_too_short(self, admin_client):
        rv = admin_client.post("/api/admin/users", json={
            "username": "ab", "password": "x123456",
        })
        assert rv.status_code == 400

        rv = admin_client.post("/api/admin/users", json={
            "username": "validname", "password": "123",
        })
        assert rv.status_code == 400


# ==========================================================================
# PATCH /api/admin/users/<id>
# ==========================================================================

class TestUpdateUser:
    def test_toggle_is_active(self, admin_client, api_app):
        uid = _user_id(api_app, "tester")
        rv = admin_client.patch(f"/api/admin/users/{uid}", json={"is_active": False})
        assert rv.status_code == 200
        assert rv.get_json()["data"]["is_active"] is False

        rv = admin_client.patch(f"/api/admin/users/{uid}", json={"is_active": True})
        assert rv.status_code == 200
        assert rv.get_json()["data"]["is_active"] is True

    def test_promote_to_admin(self, admin_client, api_app):
        uid = _user_id(api_app, "tester")
        rv = admin_client.patch(f"/api/admin/users/{uid}", json={"is_admin": True})
        assert rv.status_code == 200
        assert rv.get_json()["data"]["is_admin"] is True

    def test_demote_last_admin_returns_403(self, admin_client, api_app):
        uid = _user_id(api_app, "admin")
        rv = admin_client.patch(f"/api/admin/users/{uid}", json={"is_admin": False})
        assert rv.status_code == 403
        assert "管理员" in rv.get_json()["message"]

    def test_demote_one_of_many_admins_allowed(self, admin_client, api_app):
        tid = _user_id(api_app, "tester")
        admin_client.patch(f"/api/admin/users/{tid}", json={"is_admin": True})

        aid = _user_id(api_app, "admin")
        rv = admin_client.patch(f"/api/admin/users/{aid}", json={"is_admin": False})
        assert rv.status_code == 200
        assert rv.get_json()["data"]["is_admin"] is False

    def test_reset_password(self, admin_client, api_app):
        uid = _user_id(api_app, "tester")
        rv = admin_client.patch(f"/api/admin/users/{uid}", json={"password": "new-pass-1"})
        assert rv.status_code == 200

        # 新密码登录成功
        client = _login(api_app, "tester", "new-pass-1")
        # 旧密码登录失败
        bad = api_app.test_client()
        rv = bad.post("/api/auth/login", json={"username": "tester", "password": "tester-secret"})
        assert rv.status_code == 401

    def test_update_nonexistent_user_returns_404(self, admin_client):
        rv = admin_client.patch("/api/admin/users/99999", json={"is_active": False})
        assert rv.status_code == 404


# ==========================================================================
# DELETE /api/admin/users/<id>
# ==========================================================================

class TestDeleteUser:
    def test_cannot_delete_self(self, admin_client, api_app):
        aid = _user_id(api_app, "admin")
        rv = admin_client.delete(f"/api/admin/users/{aid}")
        assert rv.status_code == 400
        assert "自己" in rv.get_json()["message"]

    def test_can_delete_normal_user(self, admin_client, api_app):
        tid = _user_id(api_app, "tester")
        rv = admin_client.delete(f"/api/admin/users/{tid}")
        assert rv.status_code == 200

        # 删除后 tester 登录失败
        bad = api_app.test_client()
        rv = bad.post("/api/auth/login", json={"username": "tester", "password": "tester-secret"})
        assert rv.status_code == 401

    def test_cannot_delete_last_admin(self, admin2_client, api_app):
        # 把 admin2 降为普通用户,此时 admin 是唯一管理员
        aid2 = _user_id(api_app, "admin2")
        rv = admin2_client.patch(f"/api/admin/users/{aid2}", json={"is_admin": False})
        assert rv.status_code == 200

        # 用 admin2 删 admin → 应被"最后一个 admin"机制挡掉
        aid = _user_id(api_app, "admin")
        rv = admin2_client.delete(f"/api/admin/users/{aid}")
        assert rv.status_code == 403
        assert "管理员" in rv.get_json()["message"]

    def test_delete_nonexistent_user_returns_404(self, admin_client):
        rv = admin_client.delete("/api/admin/users/99999")
        assert rv.status_code == 404


# ==========================================================================
# POST /api/admin/users/<id>/regenerate-key
# ==========================================================================

class TestRegenerateApiKey:
    def test_regenerate_returns_new_key(self, admin_client, api_app):
        tid = _user_id(api_app, "tester")

        from app.models import User
        with api_app.app_context():
            old_key = User.query.get(tid).api_key

        rv = admin_client.post(f"/api/admin/users/{tid}/regenerate-key")
        assert rv.status_code == 200
        new_key = rv.get_json()["data"]["api_key"]
        assert new_key
        assert new_key != old_key

    def test_regenerate_nonexistent_returns_404(self, admin_client):
        rv = admin_client.post("/api/admin/users/99999/regenerate-key")
        assert rv.status_code == 404
