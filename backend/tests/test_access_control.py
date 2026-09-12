"""访问控制 / 风控规则测试。

覆盖:
- parse_advanced:高级设置解析(嵌套 / 扁平 / 非法 IP / 去重 / 逗号串)
- evaluate:黑名单命中、CIDR、UA、Referer、观察态、白名单未命中
- 集成:生成时规则落库、命中拦截返回 404 且不写 click_logs、visitors 鉴权、
        统计页一键拦截 → 立即生效 → 解封恢复
"""

import pytest

from app.middleware.error import BadRequestError
from app.models import (
    AccessRule,
    AccessRuleAction,
    AccessRuleMode,
    AccessRuleSource,
    ClickLog,
    ShortLink,
)
from app.services import access_control


def _rule(rule_type, value, mode=AccessRuleMode.BLOCK, action=AccessRuleAction.BLOCK):
    """构造游离规则对象(不落库),用于纯判定测试。"""
    return AccessRule(rule_type=rule_type, value=value, mode=mode, action=action)


# ---------- parse_advanced ----------

class TestParseAdvanced:
    def test_empty_inputs(self):
        assert access_control.parse_advanced(None) == []
        assert access_control.parse_advanced({}) == []
        assert access_control.parse_advanced({"access_control": {}}) == []
        assert access_control.parse_advanced("not-a-dict") == []

    def test_nested_structure(self):
        specs = access_control.parse_advanced({
            "access_control": {
                "block_ips": ["1.2.3.4", "10.0.0.0/8"],
                "block_ua": ["bot"],
                "block_referer": ["spam.example"],
                "allow_ips": ["203.0.113.0/24"],
                "action": "observe",
            }
        })
        by_key = {(s.rule_type, s.value): s for s in specs}
        assert len(specs) == 5

        assert by_key[("ip", "1.2.3.4")].mode == AccessRuleMode.BLOCK
        assert by_key[("ip", "1.2.3.4")].action == AccessRuleAction.OBSERVE
        assert by_key[("ip_cidr", "10.0.0.0/8")].mode == AccessRuleMode.BLOCK
        assert by_key[("ua", "bot")].rule_type == "ua"
        assert by_key[("referer", "spam.example")].rule_type == "referer"
        # 白名单项:mode=allow,且不受 action 影响
        assert by_key[("ip_cidr", "203.0.113.0/24")].mode == AccessRuleMode.ALLOW

    def test_flat_structure_supported(self):
        specs = access_control.parse_advanced({"block_ips": ["1.2.3.4"]})
        assert len(specs) == 1
        assert specs[0].rule_type == "ip"

    def test_comma_separated_string(self):
        specs = access_control.parse_advanced({"access_control": {"block_ua": "bot, spider"}})
        assert {s.value for s in specs} == {"bot", "spider"}

    def test_invalid_ip_raises(self):
        with pytest.raises(BadRequestError):
            access_control.parse_advanced({"access_control": {"block_ips": ["999.1.1.1"]}})

    def test_invalid_cidr_raises(self):
        with pytest.raises(BadRequestError):
            access_control.parse_advanced({"access_control": {"block_ips": ["10.0.0.0/99"]}})

    def test_dedup_same_value(self):
        specs = access_control.parse_advanced({
            "access_control": {"block_ips": ["1.2.3.4", "1.2.3.4"]}
        })
        assert len(specs) == 1


# ---------- evaluate ----------

class TestEvaluate:
    def test_no_rules_allows(self):
        d = access_control.evaluate([], ip="1.2.3.4")
        assert d.blocked is False and d.observed is False

    def test_block_ip_hit(self):
        assert access_control.evaluate([_rule("ip", "1.2.3.4")], ip="1.2.3.4").blocked is True

    def test_block_ip_miss(self):
        assert access_control.evaluate([_rule("ip", "1.2.3.4")], ip="5.6.7.8").blocked is False

    def test_cidr_hit(self):
        assert access_control.evaluate([_rule("ip_cidr", "10.0.0.0/8")], ip="10.1.2.3").blocked is True

    def test_cidr_miss(self):
        assert access_control.evaluate([_rule("ip_cidr", "10.0.0.0/8")], ip="11.0.0.1").blocked is False

    def test_ua_substring_case_insensitive(self):
        assert access_control.evaluate([_rule("ua", "BOT")], ua="my-bot/1.0").blocked is True

    def test_referer_substring(self):
        r = _rule("referer", "spam.example")
        assert access_control.evaluate([r], referer="https://spam.example/x").blocked is True
        assert access_control.evaluate([r], referer="https://good.example/x").blocked is False

    def test_observe_does_not_block(self):
        d = access_control.evaluate([_rule("ua", "bot", action=AccessRuleAction.OBSERVE)], ua="bot/1")
        assert d.observed is True and d.blocked is False

    def test_whitelist_miss_blocks(self):
        d = access_control.evaluate([_rule("ip_cidr", "203.0.113.0/24", mode=AccessRuleMode.ALLOW)], ip="1.2.3.4")
        assert d.blocked is True
        assert d.reason == "whitelist_miss"

    def test_whitelist_hit_allows(self):
        d = access_control.evaluate([_rule("ip_cidr", "203.0.113.0/24", mode=AccessRuleMode.ALLOW)], ip="203.0.113.9")
        assert d.blocked is False

    def test_whitelist_takes_priority_over_blocklist(self):
        rules = [
            _rule("ip_cidr", "203.0.113.0/24", mode=AccessRuleMode.ALLOW),
            _rule("ua", "bot"),
        ]
        # 在白名单内且 UA 命中黑名单 → 仍按黑名单拦截
        assert access_control.evaluate(rules, ip="203.0.113.9", ua="bot").blocked is True
        # 不在白名单内 → 白名单未命中直接拦
        assert access_control.evaluate(rules, ip="1.2.3.4", ua="chrome").blocked is True


# ---------- 集成:生成 → 落库 → 拦截 ----------

class TestAdvancedIntegration:
    def test_create_with_advanced_persists_rules(self, logged_in_client):
        client, user = logged_in_client
        rv = client.post("/api/shortlinks", json={
            "long_url": "https://adv.example.com/x",
            "advanced": {"access_control": {"block_ips": ["9.9.9.9"], "block_ua": ["evilbot"]}},
        })
        assert rv.status_code == 201
        code = rv.get_json()["data"]["short_code"]

        rules = AccessRule.query.filter_by(short_code=code).all()
        assert len(rules) == 2
        assert all(r.source == AccessRuleSource.ADVANCED for r in rules)
        assert all(r.scope == "short_code" for r in rules)
        assert user.id == rules[0].user_id

    def test_invalid_advanced_ip_rejected(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={
            "long_url": "https://bad-adv.example.com/",
            "advanced": {"access_control": {"block_ips": ["999.1.1.1"]}},
        })
        assert rv.status_code == 400

    def test_blocked_ip_gets_404_and_no_click_log(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={
            "long_url": "https://block-me.example.com/",
            "advanced": {"access_control": {"block_ips": ["9.9.9.9"]}},
        })
        code = rv.get_json()["data"]["short_code"]

        blocked = client.get(f"/s/{code}", headers={"X-Forwarded-For": "9.9.9.9"})
        assert blocked.status_code == 404
        # 被拦的请求不写 click_logs、不计 PV
        assert ClickLog.query.filter_by(short_code=code).count() == 0
        assert ShortLink.query.filter_by(short_code=code).first().visit_count == 0

        # 其他 IP 正常跳转并计入
        ok = client.get(f"/s/{code}", headers={"X-Forwarded-For": "8.8.8.8"})
        assert ok.status_code == 302
        assert ClickLog.query.filter_by(short_code=code).count() == 1

    def test_whitelist_from_advanced(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={
            "long_url": "https://wl.example.com/",
            "advanced": {"access_control": {"allow_ips": ["203.0.113.0/24"]}},
        })
        code = rv.get_json()["data"]["short_code"]

        assert client.get(f"/s/{code}", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 404
        assert client.get(f"/s/{code}", headers={"X-Forwarded-For": "203.0.113.7"}).status_code == 302

    def test_observe_mode_still_redirects(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={
            "long_url": "https://observe.example.com/",
            "advanced": {"access_control": {"block_ips": ["6.6.6.6"], "action": "observe"}},
        })
        code = rv.get_json()["data"]["short_code"]
        resp = client.get(f"/s/{code}", headers={"X-Forwarded-For": "6.6.6.6"})
        assert resp.status_code == 302


# ---------- 集成:统计页一键拦截 ----------

class TestManualBlockFlow:
    def test_visitors_requires_auth(self, logged_in_client, api_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={"long_url": "https://v.example.com/"})
        code = rv.get_json()["data"]["short_code"]

        assert api_client.get(f"/api/shortlinks/{code}/visitors").status_code == 401

        ok = client.get(f"/api/shortlinks/{code}/visitors?dim=ip&days=7")
        assert ok.status_code == 200
        body = ok.get_json()["data"]
        assert body["dim"] == "ip"
        assert "items" in body and "hits" in body and "rules" in body

    def test_visitors_rejects_bad_dim(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={"long_url": "https://v2.example.com/"})
        code = rv.get_json()["data"]["short_code"]
        assert client.get(f"/api/shortlinks/{code}/visitors?dim=xxx").status_code == 400

    def test_manual_block_then_unblock(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={"long_url": "https://manual.example.com/"})
        code = rv.get_json()["data"]["short_code"]

        # 拦截前可访问
        assert client.get(f"/s/{code}", headers={"X-Forwarded-For": "7.7.7.7"}).status_code == 302

        # 一键拦截
        created = client.post("/api/access-rules", json={
            "value": "7.7.7.7",
            "scope": "short_code",
            "short_code": code,
            "reason": "统计页一键拦截",
        })
        assert created.status_code == 201
        rule = created.get_json()["data"]
        assert rule["rule_type"] == "ip"
        assert rule["source"] == AccessRuleSource.MANUAL

        # 立即生效
        assert client.get(f"/s/{code}", headers={"X-Forwarded-For": "7.7.7.7"}).status_code == 404

        # 规则出现在 visitors 的 rules 里,且该行被标记为已拦截
        body = client.get(f"/api/shortlinks/{code}/visitors?dim=ip&days=7").get_json()["data"]
        assert any(r["id"] == rule["id"] for r in body["rules"])

        # 解封后恢复
        assert client.delete(f"/api/access-rules/{rule['id']}").status_code == 200
        assert client.get(f"/s/{code}", headers={"X-Forwarded-For": "7.7.7.7"}).status_code == 302

    def test_duplicate_rule_is_idempotent(self, logged_in_client):
        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={"long_url": "https://dup.example.com/"})
        code = rv.get_json()["data"]["short_code"]
        payload = {"value": "4.4.4.4", "scope": "short_code", "short_code": code}

        first = client.post("/api/access-rules", json=payload)
        second = client.post("/api/access-rules", json=payload)
        assert first.get_json()["data"]["id"] == second.get_json()["data"]["id"]
        assert AccessRule.query.filter_by(short_code=code, value="4.4.4.4").count() == 1

    def test_cannot_block_someone_elses_link(self, logged_in_client, api_app):
        """越权:不能给别人的短链加规则。"""
        from app.services import auth as auth_service

        client, _ = logged_in_client
        rv = client.post("/api/shortlinks", json={"long_url": "https://mine.example.com/"})
        code = rv.get_json()["data"]["short_code"]

        # 另一个用户
        auth_service.register("intruder", "secret456")
        other = auth_service.get_by_username("intruder")
        other_client = api_app.test_client()
        other_client.set_cookie("session", auth_service.issue_session_token(other))

        bad = other_client.post("/api/access-rules", json={
            "value": "1.1.1.1", "scope": "short_code", "short_code": code,
        })
        assert bad.status_code == 404

    def test_access_rules_requires_auth(self, api_client):
        assert api_client.get("/api/access-rules").status_code == 401
        assert api_client.post("/api/access-rules", json={"value": "1.1.1.1"}).status_code == 401
