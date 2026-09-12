"""models 集成测试:用 SQLite 内存数据库验证字段、约束、默认值。"""

import pytest

from app.models import ShortLink, ClickLog, User, Blacklist
from app.models.blacklist import Blacklist as BL
from app.models.short_link import ShortLinkStatus
from app.utils.hashing import url_hash


# ---------- ShortLink ----------

class TestShortLink:
    def test_create_minimal(self, sqlite_session):
        sl = ShortLink(
            short_code="abc123",
            long_url="https://example.com",
            url_hash=url_hash("https://example.com"),
        )
        sqlite_session.add(sl)
        sqlite_session.commit()
        assert sl.id is not None
        assert sl.status == ShortLinkStatus.ENABLED
        assert sl.is_deleted is False
        assert sl.visit_count == 0
        assert sl.created_at is not None

    def test_unique_short_code(self, sqlite_session):
        a = ShortLink(short_code="dup000", long_url="https://a.com", url_hash=url_hash("https://a.com"))
        b = ShortLink(short_code="dup000", long_url="https://b.com", url_hash=url_hash("https://b.com"))
        sqlite_session.add(a)
        sqlite_session.commit()
        sqlite_session.add(b)
        with pytest.raises(Exception):  # IntegrityError
            sqlite_session.commit()

    def test_unique_url_hash(self, sqlite_session):
        url = "https://same.com"
        a = ShortLink(short_code="c1", long_url=url, url_hash=url_hash(url))
        b = ShortLink(short_code="c2", long_url=url, url_hash=url_hash(url))
        sqlite_session.add(a)
        sqlite_session.commit()
        sqlite_session.add(b)
        with pytest.raises(Exception):
            sqlite_session.commit()

    def test_is_expired_false_when_none(self, sqlite_session):
        sl = ShortLink(short_code="ne1", long_url="https://x.com", url_hash=url_hash("https://x.com"))
        assert sl.is_expired() is False

    def test_is_expired_true_when_past(self, sqlite_session):
        from datetime import datetime, timedelta
        sl = ShortLink(
            short_code="ex1",
            long_url="https://x.com",
            url_hash=url_hash("https://x.com"),
            expire_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert sl.is_expired() is True

    def test_to_dict_keys(self, sqlite_session):
        sl = ShortLink(short_code="d1", long_url="https://x.com", url_hash=url_hash("https://x.com"))
        sqlite_session.add(sl)
        sqlite_session.commit()
        d = sl.to_dict()
        for k in ["id", "short_code", "long_url", "pv", "status",
                  "has_password", "is_deleted", "created_at"]:
            assert k in d
        assert d["has_password"] is False


# ---------- ClickLog ----------
    def test_effective_at_field_default_none(self, sqlite_session):
        sl = ShortLink(short_code="ef1", long_url="https://x.com", url_hash=url_hash("https://x.com"))
        sqlite_session.add(sl)
        sqlite_session.commit()
        assert sl.effective_at is None
        assert sl.is_not_effective() is False

    def test_is_not_effective_when_future(self, sqlite_session):
        from datetime import datetime, timedelta
        sl = ShortLink(
            short_code="ef2",
            long_url="https://x.com",
            url_hash=url_hash("https://x.com"),
            effective_at=datetime.utcnow() + timedelta(hours=2),
        )
        assert sl.is_not_effective() is True

    def test_is_effective_when_past(self, sqlite_session):
        from datetime import datetime, timedelta
        sl = ShortLink(
            short_code="ef3",
            long_url="https://x.com",
            url_hash=url_hash("https://x.com"),
            effective_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert sl.is_not_effective() is False

    def test_to_dict_includes_effective_at(self, sqlite_session):
        sl = ShortLink(short_code="ef4", long_url="https://x.com", url_hash=url_hash("https://x.com"))
        sqlite_session.add(sl)
        sqlite_session.commit()
        d = sl.to_dict()
        assert "effective_at" in d
        assert d["effective_at"] is None



class TestClickLog:
    def test_create(self, sqlite_session):
        log = ClickLog(short_code="c1", ip="1.2.3.4", user_agent="Mozilla", referer="https://ref.com")
        sqlite_session.add(log)
        sqlite_session.commit()
        assert log.id is not None
        assert log.clicked_at is not None

    def test_nullable_ua_referer(self, sqlite_session):
        log = ClickLog(short_code="c1", ip="1.2.3.4")
        sqlite_session.add(log)
        sqlite_session.commit()
        assert log.user_agent is None
        assert log.referer is None


# ---------- User ----------

class TestUser:
    def test_create(self, sqlite_session):
        u = User(username="alice", password_hash="pbkdf2_sha256$x$x$x")
        sqlite_session.add(u)
        sqlite_session.commit()
        assert u.id is not None
        assert u.created_at is not None

    def test_unique_username(self, sqlite_session):
        User(username="bob", password_hash="x")
        sqlite_session.add(_ := object()) if False else None
        u1 = User(username="bob", password_hash="x")
        u2 = User(username="bob", password_hash="y")
        sqlite_session.add(u1)
        sqlite_session.commit()
        sqlite_session.add(u2)
        with pytest.raises(Exception):
            sqlite_session.commit()


# ---------- Blacklist ----------

class TestBlacklist:
    def test_create_rule(self, sqlite_session):
        r = BL(rule_type=BL.RULE_TYPE_DOMAIN, pattern="evil.com", enabled=True)
        sqlite_session.add(r)
        sqlite_session.commit()
        assert r.id is not None
        assert r.created_at is not None

    def test_to_rule(self, sqlite_session):
        r = BL(rule_type=BL.RULE_TYPE_KEYWORD, pattern="phish")
        sqlite_session.add(r)
        sqlite_session.commit()  # 让 default=True 生效
        from app.services.security import BlacklistRule
        rule = r.to_rule()
        assert isinstance(rule, BlacklistRule)
        assert rule.rule_type == "keyword"
        assert rule.pattern == "phish"
        assert rule.enabled is True
