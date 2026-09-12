"""端到端冒烟测试:覆盖所有 API 的正常 + 异常路径。

使用 conftest 提供的 api_app / api_client fixture(SQLite 内存 + 假 Redis),
通过 Flask test_client 模拟真实 HTTP 请求。
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import (
    Blacklist,
    ClickLog,
    ShortLink,
    ShortLinkStatus,
)
from app.services.security import SecurityChecker, BlacklistRule


# ==========================================================================
# 公共:把 get_redis() 替成可控的 fake,让 health / password 等路径能跑
# ==========================================================================

class _FakeRedis:
    """最小可用 Redis:支持 ping / get / set / setex / incr / delete / zadd 等。"""
    def __init__(self):
        self.kv = {}
        self.zset = {}

    def ping(self):
        return True

    def get(self, k):
        return self.kv.get(k)

    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return False
        self.kv[k] = v
        return True

    def setex(self, k, ttl, v):
        self.kv[k] = v
        return True

    def incr(self, k):
        self.kv[k] = self.kv.get(k, 0) + 1
        return self.kv[k]

    def expire(self, k, ttl):
        return True

    def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self.kv:
                self.kv.pop(k, None)
                n += 1
        return n

    def zadd(self, k, mapping):
        s = self.zset.setdefault(k, {})
        for m, score in mapping.items():
            s[m] = score
        return len(mapping)

    def zremrangebyscore(self, k, mn, mx):
        s = self.zset.get(k, {})
        for m in [x for x, sc in s.items() if mn <= sc <= mx]:
            s.pop(m, None)
        return 1

    def zcard(self, k):
        return len(self.zset.get(k, {}))

    def zincrby(self, k, amount, m):
        s = self.zset.setdefault(k, {})
        s[m] = s.get(m, 0) + amount
        return s[m]


class _FakePool:
    connection_kwargs = {}
    decode_responses = True


def _install_fake_redis(monkeypatch):
    """把所有用到的 get_redis 引用都替换成 fake。"""
    fake = _FakeRedis()
    monkeypatch.setattr("app.extensions._redis_pool", _FakePool())
    monkeypatch.setattr("app.extensions.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.password.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.short_link.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.health.get_redis", lambda: fake)
    return fake


@pytest.fixture
def api_client(monkeypatch, api_app):
    _install_fake_redis(monkeypatch)
    return api_app.test_client()


@pytest.fixture
def auth_client(monkeypatch, api_app):
    _install_fake_redis(monkeypatch)
    client = api_app.test_client()
    client.post(
        "/api/auth/register",
        json={"username": "tester", "password": "secret123"},
    )
    rv = client.post(
        "/api/auth/login",
        json={"username": "tester", "password": "secret123"},
    )
    assert rv.status_code == 200
    return client


# ==========================================================================
# 健康检查
# ==========================================================================

class TestHealth:
    def test_health_ok(self, api_client):
        rv = api_client.get("/health")
        # /health 直接 jsonify 返回 {status,db,redis},没走统一响应包装
        assert rv.status_code == 200
        body = rv.get_json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
        assert body["redis"] == "ok"

    def test_404_unknown_path(self, api_client):
        rv = api_client.get("/this-path-does-not-exist")
        assert rv.status_code == 404


# ==========================================================================
# 鉴权
# ==========================================================================

class TestAuth:
    def test_register_login_me_logout(self, auth_client):
        c = auth_client
        rv = c.get("/api/auth/me")
        assert rv.status_code == 200
        assert rv.get_json()["data"]["username"] == "tester"

        rv = c.post("/api/auth/logout")
        assert rv.status_code == 200

        rv = c.get("/api/auth/me")
        assert rv.status_code == 401

    def test_register_validation(self, api_client):
        rv = api_client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "secret123"},
        )
        assert rv.status_code == 400

        rv = api_client.post(
            "/api/auth/register",
            json={"username": "bob", "password": "123"},
        )
        assert rv.status_code == 400

    def test_register_duplicate(self, api_client):
        # 项目 register 行为:重名返回 400 BadRequestError,不是 409
        api_client.post(
            "/api/auth/register",
            json={"username": "carol", "password": "secret123"},
        )
        rv = api_client.post(
            "/api/auth/register",
            json={"username": "carol", "password": "secret123"},
        )
        assert rv.status_code == 400
        assert "已存在" in rv.get_json()["message"]


# ==========================================================================
# 生成短链
# ==========================================================================

class TestCreateShortLink:
    def test_basic_create_201(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/a"},
        )
        assert rv.status_code == 201
        d = rv.get_json()["data"]
        assert d["long_url"] == "https://example.com/a"
        assert d["short_code"] and 6 <= len(d["short_code"]) <= 8
        assert d["full_short_url"].endswith(d["short_code"])
        assert d["status"] == "enabled"
        assert d["has_password"] is False
        assert d["pv"] == 0
        assert d["uv"] == 0

    def test_long_url_required(self, auth_client):
        rv = auth_client.post("/api/shortlinks", json={})
        assert rv.status_code == 400

    def test_long_url_too_long(self, auth_client):
        long = "https://example.com/" + "a" * 2100
        rv = auth_client.post("/api/shortlinks", json={"long_url": long})
        assert rv.status_code == 400

    def test_password_length_validation(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://x.com/1", "password": "123"},
        )
        assert rv.status_code == 400
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://x.com/2", "password": "123456789"},
        )
        assert rv.status_code == 400
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://x.com/3", "password": "abc123"},
        )
        assert rv.status_code == 201
        assert rv.get_json()["data"]["has_password"] is True

    def test_idempotency_same_long_url_same_code(self, auth_client):
        u = "https://example.com/idem/" + "x" * 50
        r1 = auth_client.post("/api/shortlinks", json={"long_url": u})
        r2 = auth_client.post("/api/shortlinks", json={"long_url": u})
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.get_json()["data"]["short_code"] == r2.get_json()["data"]["short_code"]

    def test_with_domain_channel_click_limit(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={
                "long_url": "https://example.com/c",
                "domain": "https://s.example.com",
                "channel": "wechat",
                "click_limit": 3,
            },
        )
        assert rv.status_code == 201
        d = rv.get_json()["data"]
        assert d["domain"] == "https://s.example.com"
        assert d["channel"] == "wechat"
        assert d["click_limit"] == 3
        assert d["full_short_url"].startswith("https://s.example.com/")


# ==========================================================================
# 跳转 302 + PV/UV
# ==========================================================================

class TestRedirect:
    def test_redirect_302_pv_uv(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://target.example.com/landing"},
        )
        code = rv.get_json()["data"]["short_code"]

        for _ in range(3):
            r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "10.0.0.1"})
            assert r.status_code == 302
            assert r.headers["Location"] == "https://target.example.com/landing"

        for ip in ("10.0.0.2", "10.0.0.3", "10.0.0.4"):
            r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": ip})
            assert r.status_code == 302

        rv = auth_client.get(f"/api/shortlinks/{code}/stats")
        assert rv.status_code == 200
        stats = rv.get_json()["data"]
        assert stats["pv"] >= 4
        assert stats["uv"] >= 4

    def test_redirect_404_unknown_code(self, auth_client):
        rv = auth_client.get("/s/zzzzzz")
        assert rv.status_code == 404

    def test_redirect_410_when_disabled(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/d"},
        )
        code = rv.get_json()["data"]["short_code"]
        rv = auth_client.patch(f"/api/links/{code}", json={"status": "disabled"})
        assert rv.status_code == 200
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 410
        rv = auth_client.patch(f"/api/links/{code}", json={"status": "enabled"})
        assert rv.status_code == 200
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 302

    def test_redirect_403_when_not_effective(self, auth_client):
        future = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0)
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/f", "effective_at": future.isoformat()},
        )
        assert rv.status_code == 201
        code = rv.get_json()["data"]["short_code"]
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 403

    def test_redirect_410_when_expired(self, auth_client, api_app):
        # 先建一个合法的短链(无过期时间),再直接改库写入过期时间,
        # 绕开 create 时的"过期时间不能早于当前"校验
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/expired"},
        )
        assert rv.status_code == 201
        code = rv.get_json()["data"]["short_code"]
        with api_app.app_context():
            sl = ShortLink.query.filter_by(short_code=code).first()
            sl.expire_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
        r = auth_client.get(f"/s/{code}")
        assert r.status_code == 410

    def test_redirect_410_when_click_limit_reached(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/cl", "click_limit": 2},
        )
        code = rv.get_json()["data"]["short_code"]
        # visit_count 在 redirect 时 +1;pre_check 用 >= limit
        # 第 1 次:visit_count=0 -> 通过 -> +1 后 visit_count=1
        # 第 2 次:visit_count=1 < 2 -> 通过 -> +1 后 visit_count=2
        # 第 3 次:visit_count=2 >= 2 -> GONE 410
        r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "10.1.1.1"})
        assert r.status_code == 302
        r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "10.1.1.2"})
        assert r.status_code == 302
        r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "10.1.1.3"})
        assert r.status_code == 410


# ==========================================================================
# 密码保护
# ==========================================================================

class TestPasswordProtection:
    def test_need_password_returns_401_without_cookie(self, auth_client):
        """无密码凭证 → 必须 401,即便带了错 cookie 也仍是 401。"""
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/secret", "password": "open123"},
        )
        assert rv.status_code == 201
        code = rv.get_json()["data"]["short_code"]

        # 无 cookie
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 401

    def test_wrong_password_returns_401(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/p2", "password": "open123"},
        )
        code = rv.get_json()["data"]["short_code"]

        rv = auth_client.post(
            f"/api/shortlinks/{code}/verify-password",
            json={"password": "wrongpw"},
        )
        assert rv.status_code == 401

    def test_verify_success_returns_cookie(self, auth_client):
        """正确密码 → 200 + 下发 pw_<code>=... cookie。"""
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/p3", "password": "open123"},
        )
        code = rv.get_json()["data"]["short_code"]

        rv = auth_client.post(
            f"/api/shortlinks/{code}/verify-password",
            json={"password": "open123"},
        )
        assert rv.status_code == 200
        cookies = rv.headers.getlist("Set-Cookie")
        assert any(c.startswith(f"pw_{code}=") for c in cookies)

    def test_valid_pw_cookie_lets_redirect_through(self, auth_client):
        """修复后:verify-password 拿到合法凭证,后续 /s/<code> 走 302。"""
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/p4", "password": "open123"},
        )
        code = rv.get_json()["data"]["short_code"]

        v = auth_client.post(
            f"/api/shortlinks/{code}/verify-password",
            json={"password": "open123"},
        )
        assert v.status_code == 200

        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 302
        assert rv.headers["Location"] == "https://example.com/p4"

        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 302

    def test_invalid_pw_cookie_returns_401(self, auth_client):
        """伪造/短码不匹配的 pw_<code> cookie → 401。"""
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/p5", "password": "open123"},
        )
        code = rv.get_json()["data"]["short_code"]

        # 格式错的 cookie
        auth_client.set_cookie(f"pw_{code}", "garbage")
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 401

        # 短码不匹配的合法签名 token
        from app.services.password import issue_token
        wrong = issue_token("OTHER01", 7200, "t")
        auth_client.set_cookie(f"pw_{code}", wrong)
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 401

    def test_expired_pw_cookie_returns_401(self, auth_client):
        """已过期的 pw_<code> cookie → 401。"""
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/p6", "password": "open123"},
        )
        code = rv.get_json()["data"]["short_code"]

        from app.services.password import issue_token
        expired = issue_token(code, -1, "t")
        auth_client.set_cookie(f"pw_{code}", expired)

        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 401


# ==========================================================================
# 列表 + 筛选 + 分页
# ==========================================================================

class TestListAndFilters:
    def test_pagination(self, auth_client):
        for i in range(25):
            auth_client.post(
                "/api/shortlinks",
                json={"long_url": f"https://example.com/p/{i}"},
            )
        rv = auth_client.get("/api/links?page=1&page_size=10")
        assert rv.status_code == 200
        d = rv.get_json()["data"]
        assert d["total"] == 25
        assert d["page"] == 1
        assert d["page_size"] == 10
        assert len(d["items"]) == 10

        rv = auth_client.get("/api/links?page=3&page_size=10")
        assert rv.status_code == 200
        assert len(rv.get_json()["data"]["items"]) == 5

    def test_keyword_filter(self, auth_client):
        for u in [
            "https://example.com/alpha",
            "https://example.com/beta",
            "https://other.com/alpha-other",
        ]:
            auth_client.post("/api/shortlinks", json={"long_url": u})
        rv = auth_client.get("/api/links?keyword=alpha")
        d = rv.get_json()["data"]
        assert d["total"] == 2
        for it in d["items"]:
            assert "alpha" in (it["long_url"] + it["short_code"]).lower()

    def test_channel_filter(self, auth_client):
        auth_client.post("/api/shortlinks", json={"long_url": "https://example.com/c1", "channel": "wechat"})
        auth_client.post("/api/shortlinks", json={"long_url": "https://example.com/c2", "channel": "twitter"})
        auth_client.post("/api/shortlinks", json={"long_url": "https://example.com/c3"})
        rv = auth_client.get("/api/links?channel=wechat")
        d = rv.get_json()["data"]
        assert d["total"] == 1
        assert d["items"][0]["channel"] == "wechat"

    def test_status_filter(self, auth_client):
        rv = auth_client.post("/api/shortlinks", json={"long_url": "https://x.com/s1"})
        code = rv.get_json()["data"]["short_code"]
        auth_client.patch(f"/api/links/{code}", json={"status": "disabled"})
        rv = auth_client.get("/api/links?status=disabled")
        d = rv.get_json()["data"]
        assert d["total"] >= 1
        for it in d["items"]:
            assert it["status"] == "disabled"

    def test_invalid_sort(self, auth_client):
        rv = auth_client.get("/api/links?sort=evil_sql")
        assert rv.status_code == 400


# ==========================================================================
# 软删 + 恢复
# ==========================================================================

class TestSoftDeleteAndRestore:
    def test_delete_then_404_then_restore(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/del"},
        )
        code = rv.get_json()["data"]["short_code"]

        rv = auth_client.delete(f"/api/links/{code}")
        assert rv.status_code == 200
        assert rv.get_json()["data"]["is_deleted"] is True

        # 项目语义:软删后跳转返回 404(不暴露是否曾存在),不是 410
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 404

        rv = auth_client.get("/api/links")
        codes = [it["short_code"] for it in rv.get_json()["data"]["items"]]
        assert code not in codes

        rv = auth_client.get("/api/links?include_deleted=true")
        codes = [it["short_code"] for it in rv.get_json()["data"]["items"]]
        assert code in codes

        rv = auth_client.get("/api/links?only_deleted=true")
        codes = [it["short_code"] for it in rv.get_json()["data"]["items"]]
        assert code in codes

        rv = auth_client.post(f"/api/links/{code}/restore")
        assert rv.status_code == 200
        rv = auth_client.get(f"/s/{code}")
        assert rv.status_code == 302


# ==========================================================================
# 访问控制 / 高级风控
# ==========================================================================

class TestAccessControl:
    def test_block_ip_via_advanced_rules(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={
                "long_url": "https://example.com/ac",
                "advanced": {
                    "access_control": {
                        "block_ips": ["192.168.99.99"],
                        "action": "block",
                    }
                },
            },
        )
        assert rv.status_code == 201
        code = rv.get_json()["data"]["short_code"]

        r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "10.0.0.1"})
        assert r.status_code == 302

        r = auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "192.168.99.99"})
        assert r.status_code == 404


# ==========================================================================
# 恶意链接拦截
# ==========================================================================

class TestMaliciousURL:
    def test_security_checker_unit(self):
        """SecurityChecker 单元行为:domain / keyword / regex / 启停 / fail_open。"""
        c = SecurityChecker(
            rules=[BlacklistRule("domain", "evil.example.com", enabled=True)],
            enabled=True, fail_open=False,
        )
        assert c.is_malicious("https://evil.example.com/x") is True
        assert c.is_malicious("https://good.example.com/x") is False

        c2 = SecurityChecker(
            rules=[BlacklistRule("keyword", "phish", enabled=True)],
            enabled=True, fail_open=False,
        )
        assert c2.is_malicious("https://x.com/phish-page") is True
        assert c2.is_malicious("https://x.com/safe") is False

        c3 = SecurityChecker(
            rules=[BlacklistRule("regex", r".*evil.*", enabled=True)],
            enabled=True, fail_open=False,
        )
        assert c3.is_malicious("https://x.com/evil") is True
        assert c3.is_malicious("https://x.com/safe") is False

        # 启停
        c4 = SecurityChecker(
            rules=[BlacklistRule("domain", "evil.com", enabled=False)],
            enabled=True, fail_open=False,
        )
        assert c4.is_malicious("https://evil.com/x") is False

        # 总开关
        c5 = SecurityChecker(
            rules=[BlacklistRule("domain", "evil.com", enabled=True)],
            enabled=False, fail_open=False,
        )
        assert c5.is_malicious("https://evil.com/x") is False

    def test_redirect_blocked_when_marked_malicious(self, auth_client, api_app):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/m"},
        )
        code = rv.get_json()["data"]["short_code"]
        with api_app.app_context():
            sl = ShortLink.query.filter_by(short_code=code).first()
            sl.status = ShortLinkStatus.MALICIOUS
            db.session.commit()
        r = auth_client.get(f"/s/{code}")
        assert r.status_code == 403


# ==========================================================================
# 统计接口
# ==========================================================================

class TestStats:
    def test_overview_requires_login(self, api_client):
        rv = api_client.get("/api/stats/overview")
        assert rv.status_code == 401

    def test_overview_basic(self, auth_client):
        for i in range(3):
            auth_client.post("/api/shortlinks", json={"long_url": f"https://x.com/o/{i}"})
        rv = auth_client.get("/api/links?page_size=1")
        items = rv.get_json()["data"]["items"]
        assert items
        code = items[0]["short_code"]
        for ip in ("1.1.1.1", "2.2.2.2"):
            auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": ip})

        rv = auth_client.get("/api/stats/overview?days=7")
        assert rv.status_code == 200
        d = rv.get_json()["data"]
        assert d.get("total_links", d.get("total", 0)) >= 3

    def test_per_link_stats(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/ps"},
        )
        code = rv.get_json()["data"]["short_code"]
        for ip in ("5.5.5.1", "5.5.5.2", "5.5.5.3"):
            auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": ip})

        rv = auth_client.get(f"/api/shortlinks/{code}/stats")
        assert rv.status_code == 200
        d = rv.get_json()["data"]
        assert d["pv"] == 3
        assert d["uv"] == 3

    def test_visitors_endpoint(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/v"},
        )
        code = rv.get_json()["data"]["short_code"]
        auth_client.get(f"/s/{code}", environ_overrides={
            "REMOTE_ADDR": "8.8.8.8",
            "HTTP_USER_AGENT": "Mozilla/5.0 (Macintosh)",
            "HTTP_REFERER": "https://google.com/",
        })
        rv = auth_client.get(f"/api/shortlinks/{code}/visitors")
        assert rv.status_code == 200

    def test_trend_endpoint(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/t"},
        )
        code = rv.get_json()["data"]["short_code"]
        auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "9.9.9.9"})
        rv = auth_client.get(f"/api/shortlinks/{code}/trend?days=7")
        assert rv.status_code == 200

    def test_breakdown_endpoint(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/b"},
        )
        code = rv.get_json()["data"]["short_code"]
        auth_client.get(f"/s/{code}", environ_overrides={
            "REMOTE_ADDR": "7.7.7.7",
            "HTTP_USER_AGENT": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
        })
        for dim in ("device", "os", "browser", "referer_type", "geo"):
            rv = auth_client.get(f"/api/shortlinks/{code}/breakdown?dim={dim}")
            assert rv.status_code == 200, dim

    def test_export_csv(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/exp"},
        )
        code = rv.get_json()["data"]["short_code"]
        auth_client.get(f"/s/{code}", environ_overrides={"REMOTE_ADDR": "6.6.6.6"})
        rv = auth_client.get(f"/api/shortlinks/{code}/export")
        assert rv.status_code == 200
        ct = rv.headers.get("Content-Type", "").lower()
        assert "csv" in ct or "text" in ct
        # 实际导出列头是中文(IP / 时间(UTC) / 设备类型 等)
        body = rv.data.decode("utf-8-sig")
        assert "IP" in body and "时间" in body


# ==========================================================================
# ClickLog 持久化校验
# ==========================================================================

class TestClickLog:
    def test_click_log_row_created(self, auth_client):
        rv = auth_client.post(
            "/api/shortlinks",
            json={"long_url": "https://example.com/cl"},
        )
        code = rv.get_json()["data"]["short_code"]
        auth_client.get(f"/s/{code}", environ_overrides={
            "REMOTE_ADDR": "4.4.4.4",
            "HTTP_USER_AGENT": "TestAgent/1.0",
            "HTTP_REFERER": "https://ref.example/",
        })
        with auth_client.application.app_context():
            logs = ClickLog.query.filter_by(short_code=code).all()
            assert len(logs) == 1
            assert logs[0].ip == "4.4.4.4"
            assert logs[0].user_agent == "TestAgent/1.0"
            assert logs[0].referer == "https://ref.example/"
