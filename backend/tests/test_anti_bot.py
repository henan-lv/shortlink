"""services.anti_bot 单测。"""

from app.services.anti_bot import AntiBotChecker, build_anti_bot


class TestDisabled:
    def test_disabled_never_suspicious(self):
        c = AntiBotChecker(ua_pattern="bot", enabled=False, block=True)
        assert c.check("Googlebot/2.1").suspicious is False
        assert c.check("Googlebot/2.1").blocked is False


class TestEnabled:
    def test_match_keyword(self):
        c = AntiBotChecker(ua_pattern="bot", enabled=True, block=False)
        r = c.check("Mozilla/5.0 (compatible; Googlebot/2.1)")
        assert r.suspicious is True
        assert r.blocked is False

    def test_match_case_insensitive(self):
        c = AntiBotChecker(ua_pattern="bot|crawl", enabled=True, block=True)
        r = c.check("CRAWLER-X")
        assert r.suspicious is True
        assert r.blocked is True

    def test_no_match(self):
        c = AntiBotChecker(ua_pattern="bot", enabled=True, block=True)
        r = c.check("Mozilla/5.0 (Macintosh)")
        assert r.suspicious is False
        assert r.blocked is False

    def test_empty_ua_not_suspicious(self):
        c = AntiBotChecker(ua_pattern="bot", enabled=True, block=True)
        assert c.check("").suspicious is False
        assert c.check(None).suspicious is False

    def test_invalid_regex_disables(self):
        c = AntiBotChecker(ua_pattern="[invalid", enabled=True, block=True)
        assert c.check("anything-bot").suspicious is False


class TestBuild:
    def test_build(self):
        c = build_anti_bot("bot", True, False)
        r = c.check("mybot/1.0")
        assert r.suspicious is True
        assert r.blocked is False
