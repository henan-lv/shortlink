"""总览级聚合 API 测试(跨用户链接聚合的 trend / breakdown / realtime)。

覆盖:
- /api/stats/overview/trend        跨链接点击趋势
- /api/stats/overview/breakdown    跨链接来源/设备/浏览器/系统/地理
- /api/stats/overview/realtime     跨链接最近访问实时窗口

鉴权:必须登录;只统计当前用户。
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import ClickLog, ShortLink, User


def _register_and_login(client, username="overview_user", password="secret123"):
    client.post("/api/auth/register", json={
        "username": username, "password": password,
    })
    rv = client.post("/api/auth/login", json={
        "username": username, "password": password,
    })
    assert rv.status_code == 200


def _create_short(client, long_url, **extra):
    r = client.post("/api/shortlinks", json={"long_url": long_url, **extra})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]["short_code"]


def _click(client, short_code, ua="Mozilla/5.0 (Macintosh)", referer="",
           when=None, ip="10.0.0.1"):
    """模拟一次跳转:直接插 click_log(更可控,不走完整 302)。"""
    log = ClickLog(
        short_code=short_code,
        ip=ip,
        user_agent=ua,
        referer=referer,
        clicked_at=when or datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()
    return log


# ==========================================================================
# GET /api/stats/overview/trend
# ==========================================================================

class TestOverviewTrend:
    def test_requires_login(self, api_client):
        rv = api_client.get("/api/stats/overview/trend")
        assert rv.status_code == 401

    def test_empty_no_links(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.get("/api/stats/overview/trend?days=7&granularity=day")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        assert body["granularity"] == "day"
        assert body["days"] == 7
        # 7 个连续天点,所有 PV/UV 为 0(连续性)
        assert len(body["points"]) == 8  # 7 days back to today inclusive
        assert all(p["pv"] == 0 for p in body["points"])
        assert body["total_pv"] == 0

    def test_aggregates_across_links(self, logged_in_client):
        client, user = logged_in_client
        c1 = _create_short(client, "https://agg-1.com")
        c2 = _create_short(client, "https://agg-2.com")
        _click(client, c1, ip="1.1.1.1", when=datetime.utcnow())
        _click(client, c1, ip="1.1.1.1", when=datetime.utcnow())
        _click(client, c2, ip="2.2.2.2", when=datetime.utcnow())
        rv = client.get("/api/stats/overview/trend?days=7&granularity=day")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        # 两条链接的总 PV = 3
        assert body["total_pv"] == 3
        assert body["total_uv"] >= 2  # 两条链接的 IP 默认不同

    def test_uv_dedup_within_day(self, logged_in_client):
        client, _ = logged_in_client
        code = _create_short(client, "https://dedup.com")
        now = datetime.utcnow()
        # 同一 IP 在同一天点 3 次,UV 应该是 1
        _click(client, code, ip="1.2.3.4", when=now)
        _click(client, code, ip="1.2.3.4", when=now)
        _click(client, code, ip="1.2.3.4", when=now)
        rv = client.get("/api/stats/overview/trend?days=1&granularity=day")
        body = rv.get_json()["data"]
        # total_pv=3, 当天 UV=1
        assert body["total_pv"] == 3
        # 总 UV 不是 day 级别求和(可能跨天去重),这里校验 day 桶内 UV
        non_zero = [p for p in body["points"] if p["pv"] > 0]
        assert non_zero[0]["uv"] == 1

    def test_excludes_other_users_links(self, logged_in_client, api_client):
        """用户 A 的链接不计入用户 B 的总览。"""
        client_a, _ = logged_in_client
        client_b = api_client.test_client() if hasattr(api_client, "test_client") else api_client
        # 重新走一遍:用同一个 fixture 的 client(共享 api_app)
        _register_and_login(client_a, "user_a", "secret123")
        code_a = _create_short(client_a, "https://only-a.com")
        _click(client_a, code_a)

        # 用户 B 登录
        _register_and_login(client_b, "user_b", "secret123")
        rv = client_b.get("/api/stats/overview/trend?days=7&granularity=day")
        body = rv.get_json()["data"]
        assert body["total_pv"] == 0

    def test_excludes_deleted_links(self, logged_in_client):
        client, _ = logged_in_client
        code = _create_short(client, "https://todelete.com")
        _click(client, code)
        # 软删
        client.delete(f"/api/links/{code}")
        rv = client.get("/api/stats/overview/trend?days=7&granularity=day")
        body = rv.get_json()["data"]
        # 软删后该短码的 click_log 不再计入当前用户
        assert body["total_pv"] == 0

    def test_invalid_granularity(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.get("/api/stats/overview/trend?granularity=year")
        assert rv.status_code == 400

    def test_hour_granularity_caps_days(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.get("/api/stats/overview/trend?granularity=hour&days=30")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        assert body["days"] == 7  # 被截断到 hour 维度的上限


# ==========================================================================
# GET /api/stats/overview/breakdown
# ==========================================================================

class TestOverviewBreakdown:
    def test_requires_login(self, api_client):
        rv = api_client.get("/api/stats/overview/breakdown")
        assert rv.status_code == 401

    def test_device_breakdown(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://dev1.com")
        _click(client, c1, ua="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)")
        _click(client, c1, ua="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)")
        _click(client, c1, ua="Mozilla/5.0 (Macintosh)")
        rv = client.get("/api/stats/overview/breakdown?by=device&days=7")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        assert body["by"] == "device"
        assert body["total"] == 3
        items = {x["value"]: x["pv"] for x in body["items"]}
        assert items.get("手机", 0) == 2
        assert items.get("桌面", 0) == 1

    def test_browser_breakdown(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://br.com")
        _click(client, c1, ua="Mozilla/5.0 Chrome/120")
        _click(client, c1, ua="Mozilla/5.0 Safari/605")
        rv = client.get("/api/stats/overview/breakdown?by=browser&days=7")
        body = rv.get_json()["data"]
        assert body["total"] == 2
        items = {x["value"]: x["pv"] for x in body["items"]}
        assert "Chrome" in items
        assert "Safari" in items

    def test_referer_type_breakdown(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://ref.com")
        _click(client, c1, referer="")  # 直接访问
        _click(client, c1, referer="https://google.com/search?q=x")
        _click(client, c1, referer="https://t.co/share/abc")
        rv = client.get("/api/stats/overview/breakdown?by=referer_type&days=7")
        body = rv.get_json()["data"]
        assert body["total"] == 3
        items = {x["value"]: x["pv"] for x in body["items"]}
        assert items.get("直接访问", 0) >= 1
        assert items.get("搜索引擎", 0) >= 1

    def test_geo_breakdown_without_ipdb(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://geo.com")
        _click(client, c1, ip="8.8.8.8")
        rv = client.get("/api/stats/overview/breakdown?by=geo&level=country&days=7")
        body = rv.get_json()["data"]
        assert body["by"] == "geo"
        # 没有 IP 库时 available=false,类目至少包含「内网/未知」
        assert body["available"] is False

    def test_invalid_by(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.get("/api/stats/overview/breakdown?by=invalid")
        assert rv.status_code == 400

    def test_invalid_geo_level(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.get("/api/stats/overview/breakdown?by=geo&level=block")
        assert rv.status_code == 400

    def test_excludes_other_users(self, logged_in_client, api_client):
        client_a, _ = logged_in_client
        code = _create_short(client_a, "https://isolation.com")
        _click(client_a, code, ua="Mozilla/5.0 (iPhone)")
        # user_b 看应为空
        client_b = api_client.test_client() if hasattr(api_client, "test_client") else api_client
        _register_and_login(client_b, "user_b2", "secret123")
        rv = client_b.get("/api/stats/overview/breakdown?by=device&days=7")
        body = rv.get_json()["data"]
        assert body["total"] == 0


# ==========================================================================
# GET /api/stats/overview/realtime
# ==========================================================================

class TestOverviewRealtime:
    def test_requires_login(self, api_client):
        rv = api_client.get("/api/stats/overview/realtime")
        assert rv.status_code == 401

    def test_empty(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.get("/api/stats/overview/realtime?minutes=30")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        assert body["window_minutes"] == 30
        assert body["count"] == 0
        assert body["top_links"] == []
        assert body["latest"] == []

    def test_counts_recent_clicks(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://rt-1.com")
        c2 = _create_short(client, "https://rt-2.com")
        now = datetime.utcnow()
        # 窗口内:2 + 3
        _click(client, c1, when=now - timedelta(minutes=10))
        _click(client, c1, when=now - timedelta(minutes=15))
        _click(client, c2, when=now - timedelta(minutes=20))
        _click(client, c2, when=now - timedelta(minutes=25))
        _click(client, c2, when=now - timedelta(minutes=29))
        # 窗口外(35 分钟前)不应计入
        _click(client, c1, when=now - timedelta(minutes=35))
        rv = client.get("/api/stats/overview/realtime?minutes=30")
        body = rv.get_json()["data"]
        assert body["count"] == 5
        assert len(body["latest"]) == 5

    def test_top_links_ordered_by_pv(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://top-1.com")
        c2 = _create_short(client, "https://top-2.com")
        c3 = _create_short(client, "https://top-3.com")
        now = datetime.utcnow()
        for _ in range(3):
            _click(client, c1, when=now)
        for _ in range(5):
            _click(client, c2, when=now)
        for _ in range(1):
            _click(client, c3, when=now)
        rv = client.get("/api/stats/overview/realtime?minutes=30")
        body = rv.get_json()["data"]
        top = body["top_links"]
        assert len(top) == 3
        assert top[0]["short_code"] == c2
        assert top[0]["pv"] == 5
        assert top[1]["short_code"] == c1
        assert top[2]["short_code"] == c3

    def test_latest_no_ip_leak(self, logged_in_client):
        client, _ = logged_in_client
        c1 = _create_short(client, "https://leak.com")
        _click(client, c1, ip="9.9.9.9", ua="Mozilla/5.0 (iPhone)")
        rv = client.get("/api/stats/overview/realtime?minutes=30")
        body = rv.get_json()["data"]
        latest = body["latest"]
        assert len(latest) >= 1
        # latest 项不应该包含 ip 字段(隐私)
        assert "ip" not in latest[0]
        assert latest[0]["short_code"] == c1
        assert latest[0]["device"] == "手机"

    def test_window_minutes_bounds(self, logged_in_client):
        client, _ = logged_in_client
        # minutes 超界会被截断
        rv = client.get("/api/stats/overview/realtime?minutes=99999")
        assert rv.status_code == 200
        body = rv.get_json()["data"]
        assert body["window_minutes"] <= 1440

    def test_excludes_other_users(self, logged_in_client, api_client):
        client_a, _ = logged_in_client
        code = _create_short(client_a, "https://iso-rt.com")
        _click(client_a, code)
        client_b = api_client.test_client() if hasattr(api_client, "test_client") else api_client
        _register_and_login(client_b, "user_b3", "secret123")
        rv = client_b.get("/api/stats/overview/realtime?minutes=30")
        body = rv.get_json()["data"]
        assert body["count"] == 0
