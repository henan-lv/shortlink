"""services.security 单测。"""

import pytest

from app.services.security import BlacklistRule, SecurityChecker


def _checker(rules=None, enabled=True, fail_open=False):
    return SecurityChecker(rules=rules, enabled=enabled, fail_open=fail_open)


class TestDisabled:
    def test_disabled_never_malicious(self):
        c = _checker([BlacklistRule("domain", "evil.com")], enabled=False)
        assert not c.is_malicious("https://evil.com/x")


class TestNoRules:
    def test_no_rules_pass_through(self):
        c = _checker(rules=None)
        assert not c.is_malicious("https://example.com")


class TestExact:
    def test_exact_match(self):
        c = _checker([BlacklistRule("exact", "https://evil.com/bad")])
        assert c.is_malicious("https://evil.com/bad")
        assert not c.is_malicious("https://evil.com/good")


class TestDomain:
    def test_domain_match(self):
        c = _checker([BlacklistRule("domain", "evil.com")])
        assert c.is_malicious("https://evil.com/")
        assert c.is_malicious("http://EVIL.com/path")
        assert not c.is_malicious("https://good.com/")


class TestKeyword:
    def test_keyword_substring(self):
        c = _checker([BlacklistRule("keyword", "phish")])
        assert c.is_malicious("https://example.com/phishing")
        assert c.is_malicious("https://x.com/PHISH-attack")
        assert not c.is_malicious("https://example.com/legit")


class TestRegex:
    def test_regex_match(self):
        c = _checker([BlacklistRule("regex", r"^https?://(\d+\.){3}\d+")])
        assert c.is_malicious("http://1.2.3.4/")
        assert not c.is_malicious("https://example.com/")

    def test_invalid_regex_silently_skipped(self):
        c = _checker([BlacklistRule("regex", r"[invalid")])
        assert not c.is_malicious("https://example.com/")


class TestMultipleRules:
    def test_any_match(self):
        c = _checker([
            BlacklistRule("domain", "evil.com"),
            BlacklistRule("keyword", "spam"),
        ])
        assert c.is_malicious("https://evil.com/")
        assert c.is_malicious("https://good.com/spam")
        assert not c.is_malicious("https://good.com/legit")


class TestDisabledRule:
    def test_disabled_rule_ignored(self):
        c = _checker([
            BlacklistRule("domain", "evil.com", enabled=False),
        ])
        assert not c.is_malicious("https://evil.com/")


class TestFailOpen:
    def test_no_rules_with_fail_open(self):
        # 无规则 + fail_open=True → 放行
        c = _checker(rules=None, fail_open=True)
        assert not c.is_malicious("https://example.com")
