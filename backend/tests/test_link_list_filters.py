"""链接列表:筛选 / 排序 / 分页 测试。

覆盖:
- keyword:命中短码、命中长链子串、无命中、空白串不筛选、% 与 _ 按字面量处理
- channel / domain:精确匹配
- sort:创建时间升降序、PV 降序、非法值 400
- 组合筛选:status + keyword、回收站 + keyword
- 分页:offset 正确、page_size 上限
- 越权:关键词搜索不跨用户
"""

from urllib.parse import urlencode

from app.extensions import db
from app.models import ShortLink


def _create(client, long_url, **extra):
    body = {"long_url": long_url}
    body.update(extra)
    resp = client.post("/api/shortlinks", json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


def _list(client, **params):
    qs = urlencode(params)
    resp = client.get(f"/api/links?{qs}" if qs else "/api/links")
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]


def _codes(client, **params):
    return [row["short_code"] for row in _list(client, **params)["items"]]


class TestKeywordFilter:
    def test_matches_short_code(self, logged_in_client):
        client, _ = logged_in_client
        a = _create(client, "https://alpha.example.com/x")
        _create(client, "https://beta.example.com/y")

        data = _list(client, keyword=a["short_code"])
        assert data["total"] == 1
        assert data["items"][0]["short_code"] == a["short_code"]

    def test_matches_long_url_substring(self, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x")
        _create(client, "https://beta.example.com/y")

        data = _list(client, keyword="alpha")
        assert data["total"] == 1
        assert "alpha" in data["items"][0]["long_url"]

    def test_no_match_returns_empty(self, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x")

        data = _list(client, keyword="definitely-not-there")
        assert data["total"] == 0
        assert data["items"] == []

    def test_blank_keyword_does_not_filter(self, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x")
        _create(client, "https://beta.example.com/y")

        assert _list(client, keyword="")["total"] == 2
        assert _list(client, keyword="   ")["total"] == 2

    def test_percent_treated_as_literal(self, logged_in_client):
        """% 是 LIKE 通配符,必须被转义,否则搜索 % 会命中全部。"""
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x")
        _create(client, "https://beta.example.com/y")

        assert _list(client, keyword="%")["total"] == 0

    def test_underscore_treated_as_literal(self, logged_in_client):
        """_ 匹配任意单字符,必须被转义。"""
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x")

        assert _list(client, keyword="_")["total"] == 0

    def test_keyword_scoped_to_own_links(self, api_app, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://secret-alpha.example.com/x")

        other = api_app.test_client()
        other.post("/api/auth/register", json={"username": "other", "password": "secret123"})
        other.post("/api/auth/login", json={"username": "other", "password": "secret123"})

        assert _list(other, keyword="alpha")["total"] == 0


class TestChannelDomainFilter:
    def test_channel_exact_match(self, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x", channel="wechat")
        _create(client, "https://beta.example.com/y", channel="app")

        data = _list(client, channel="wechat")
        assert data["total"] == 1
        assert data["items"][0]["channel"] == "wechat"

    def test_channel_partial_does_not_match(self, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x", channel="wechat")

        assert _list(client, channel="wech")["total"] == 0

    def test_domain_exact_match(self, logged_in_client):
        client, _ = logged_in_client
        _create(client, "https://alpha.example.com/x", domain="s.example.com")
        _create(client, "https://beta.example.com/y")

        data = _list(client, domain="s.example.com")
        assert data["total"] == 1
        assert data["items"][0]["domain"] == "s.example.com"


class TestSort:
    def test_created_asc(self, logged_in_client):
        client, _ = logged_in_client
        a = _create(client, "https://alpha.example.com/x")
        b = _create(client, "https://beta.example.com/y")

        assert _codes(client, sort="created_asc") == [a["short_code"], b["short_code"]]

    def test_created_desc_is_default(self, logged_in_client):
        client, _ = logged_in_client
        a = _create(client, "https://alpha.example.com/x")
        b = _create(client, "https://beta.example.com/y")

        assert _codes(client) == [b["short_code"], a["short_code"]]

    def test_pv_desc(self, logged_in_client):
        client, _ = logged_in_client
        a = _create(client, "https://alpha.example.com/x")
        b = _create(client, "https://beta.example.com/y")

        # 直接改 PV,不依赖跳转链路
        ShortLink.query.filter_by(short_code=a["short_code"]).update({"visit_count": 5})
        ShortLink.query.filter_by(short_code=b["short_code"]).update({"visit_count": 1})
        db.session.commit()

        assert _codes(client, sort="pv_desc") == [a["short_code"], b["short_code"]]

    def test_invalid_sort_rejected(self, logged_in_client):
        client, _ = logged_in_client
        assert client.get("/api/links?sort=nope").status_code == 400


class TestCombinedFilters:
    def test_status_and_keyword(self, logged_in_client):
        client, _ = logged_in_client
        a = _create(client, "https://alpha.example.com/x")
        _create(client, "https://alpha.example.com/y")
        client.patch(f"/api/links/{a['short_code']}", json={"status": "disabled"})

        data = _list(client, keyword="alpha", status="disabled")
        assert data["total"] == 1
        assert data["items"][0]["short_code"] == a["short_code"]

    def test_recycle_bin_with_keyword(self, logged_in_client):
        client, _ = logged_in_client
        a = _create(client, "https://alpha.example.com/x")
        _create(client, "https://beta.example.com/y")
        client.delete(f"/api/links/{a['short_code']}")

        data = _list(client, only_deleted="true", keyword="alpha")
        assert data["total"] == 1
        row = data["items"][0]
        assert row["short_code"] == a["short_code"]
        assert row["is_deleted"] is True


class TestPagination:
    def test_offset_follows_page_size(self, logged_in_client):
        client, _ = logged_in_client
        codes = [_create(client, f"https://alpha.example.com/p{i}")["short_code"] for i in range(5)]

        first = _list(client, page=1, page_size=2, sort="created_asc")
        assert first["total"] == 5
        assert [r["short_code"] for r in first["items"]] == codes[:2]

        third = _list(client, page=3, page_size=2, sort="created_asc")
        assert [r["short_code"] for r in third["items"]] == codes[4:]

    def test_page_size_upper_bound(self, logged_in_client):
        client, _ = logged_in_client
        assert client.get("/api/links?page_size=101").status_code == 400
        assert client.get("/api/links?page_size=100").status_code == 200
