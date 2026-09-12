"""软删可恢复(回收站)测试。

覆盖:
- 软删后:默认列表不可见 / 回收站可见 / 跳转 404
- 恢复:url_hash 精确还原 / 回到默认列表 / 跳转恢复 302
- 幂等:重复软删、恢复活跃链接均无副作用
- 冲突:软删期间同链被重新生成 -> 409,不做合并
- 边界:自定义域名 + 渠道参与哈希还原
- 鉴权:未登录 401 / 越权 404
"""

from app.models import ShortLink
from app.utils.hashing import url_hash


LONG = "https://example.com/landing?a=1"


def _create(client, **extra):
    body = {"long_url": LONG}
    body.update(extra)
    resp = client.post("/api/shortlinks", json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]


def _db_link(code):
    return ShortLink.query.filter_by(short_code=code).first()


class TestSoftDelete:
    def test_delete_hides_from_default_list(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]

        assert client.delete(f"/api/links/{code}").status_code == 200

        default = client.get("/api/links").get_json()["data"]
        assert default["total"] == 0
        assert default["items"] == []

    def test_delete_shows_in_recycle_bin(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        client.delete(f"/api/links/{code}")

        trash = client.get("/api/links?only_deleted=true").get_json()["data"]
        assert trash["total"] == 1
        row = trash["items"][0]
        assert row["short_code"] == code
        assert row["is_deleted"] is True
        assert row["deleted_at"] is not None

    def test_deleted_link_redirects_404(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        assert client.get(f"/s/{code}").status_code == 302

        client.delete(f"/api/links/{code}")
        assert client.get(f"/s/{code}").status_code == 404

    def test_double_delete_is_idempotent(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]

        assert client.delete(f"/api/links/{code}").status_code == 200
        first = _db_link(code)
        first_deleted_at = first.deleted_at
        first_hash = first.url_hash

        assert client.delete(f"/api/links/{code}").status_code == 200
        again = _db_link(code)
        assert again.url_hash == first_hash
        assert again.deleted_at == first_deleted_at


class TestRestore:
    def test_restore_recomputes_original_hash(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        expected = url_hash(LONG, "", "")

        assert _db_link(code).url_hash == expected

        client.delete(f"/api/links/{code}")
        assert _db_link(code).url_hash == f"del-{_db_link(code).id}"

        resp = client.post(f"/api/links/{code}/restore")
        assert resp.status_code == 200, resp.get_json()

        sl = _db_link(code)
        assert sl.url_hash == expected
        assert sl.is_deleted is False
        assert sl.deleted_at is None
        assert resp.get_json()["data"]["is_deleted"] is False

    def test_restore_returns_link_to_default_list(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        client.delete(f"/api/links/{code}")
        client.post(f"/api/links/{code}/restore")

        default = client.get("/api/links").get_json()["data"]
        assert default["total"] == 1
        assert default["items"][0]["short_code"] == code

        trash = client.get("/api/links?only_deleted=true").get_json()["data"]
        assert trash["total"] == 0

    def test_restore_makes_redirect_work_again(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        client.delete(f"/api/links/{code}")
        assert client.get(f"/s/{code}").status_code == 404

        client.post(f"/api/links/{code}/restore")
        resp = client.get(f"/s/{code}")
        assert resp.status_code == 302
        assert resp.headers["Location"] == LONG

    def test_delete_restore_delete_round_trips(self, logged_in_client):
        """反复软删/恢复不应破坏哈希(占位符被正确覆盖)。"""
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        expected = url_hash(LONG, "", "")

        for _ in range(3):
            client.delete(f"/api/links/{code}")
            assert _db_link(code).url_hash.startswith("del-")
            client.post(f"/api/links/{code}/restore")
            assert _db_link(code).url_hash == expected

    def test_restore_active_link_is_noop(self, logged_in_client):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        before = _db_link(code)
        before_hash = before.url_hash

        resp = client.post(f"/api/links/{code}/restore")
        assert resp.status_code == 200

        after = _db_link(code)
        assert after.url_hash == before_hash
        assert after.is_deleted is False
        assert after.deleted_at is None

    def test_restore_conflicts_when_same_url_regenerated(self, logged_in_client):
        """软删期间同一条长链被重新生成 -> 拒绝恢复,避免撞唯一索引。"""
        client, _user = logged_in_client
        old_code = _create(client)["short_code"]
        client.delete(f"/api/links/{old_code}")

        new_code = _create(client)["short_code"]
        assert new_code != old_code

        resp = client.post(f"/api/links/{old_code}/restore")
        assert resp.status_code == 409
        assert new_code in resp.get_json()["message"]

        # 旧记录保持软删状态,新记录不受影响
        assert _db_link(old_code).is_deleted is True
        assert _db_link(new_code).is_deleted is False
        assert client.get(f"/s/{new_code}").status_code == 302

    def test_restore_preserves_domain_channel_hash(self, logged_in_client):
        """自定义域名 + 渠道参与哈希,恢复时必须一并还原。"""
        client, _user = logged_in_client
        code = _create(client, domain="https://s.example.com", channel="wechat")["short_code"]
        expected = url_hash(LONG, "https://s.example.com", "wechat")
        assert _db_link(code).url_hash == expected

        client.delete(f"/api/links/{code}")
        client.post(f"/api/links/{code}/restore")

        sl = _db_link(code)
        assert sl.url_hash == expected
        assert sl.domain == "https://s.example.com"
        assert sl.channel == "wechat"


class TestRestoreAuth:
    def test_requires_login(self, api_client):
        assert api_client.post("/api/links/abcdef/restore").status_code == 401

    def test_cannot_restore_other_users_link(self, logged_in_client, api_app):
        client, _user = logged_in_client
        code = _create(client)["short_code"]
        client.delete(f"/api/links/{code}")

        # 另一个用户
        from app.services import auth as auth_service
        auth_service.register("intruder", "secret123")
        other = auth_service.get_by_username("intruder")
        token = auth_service.issue_session_token(other)
        intruder = api_app.test_client()
        intruder.set_cookie("session", token)

        assert intruder.post(f"/api/links/{code}/restore").status_code == 404
        assert _db_link(code).is_deleted is True

    def test_unknown_code_returns_404(self, logged_in_client):
        client, _user = logged_in_client
        assert client.post("/api/links/nope99/restore").status_code == 404
