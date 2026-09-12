# -*- coding: utf-8 -*-
"""\u81ea\u5b9a\u4e49\u57df\u540d + \u6e20\u9053 + JSON \u9ad8\u7ea7\u8bbe\u7f6e \u7684\u96c6\u6210\u6d4b\u8bd5\u3002"""

import pytest

from app.extensions import db
from app.models import ShortLink
from app.services import short_link as svc
from app.utils.hashing import url_hash
from app.schemas.short_link import CreateShortLinkRequest


# ---------- \u5b8c\u6574 config \u7684 SQLite fixture ----------

@pytest.fixture
def sqlite_app(monkeypatch):
    """SQLite \u5185\u5b58\u6570\u636e\u5e93 + \u5b8c\u6574 app.config\u3002"""
    from flask import Flask
    from app.extensions import db as _db
    from app import models  # noqa: F401

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
        SECURITY_ENABLED=False,
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
    monkeypatch.setattr("app.config.validate_config", lambda cfg: None)
    _db.init_app(app)

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


# ---------- url_hash \u51fd\u6570 ----------

class TestUrlHash:
    def test_same_inputs_same_hash(self):
        assert url_hash("https://a.com") == url_hash("https://a.com")
        assert url_hash("https://a.com", "s.example.com", "wechat") == url_hash("https://a.com", "s.example.com", "wechat")

    def test_different_domain_different_hash(self):
        assert url_hash("https://a.com", "s1.example.com") != url_hash("https://a.com", "s2.example.com")

    def test_different_channel_different_hash(self):
        assert url_hash("https://a.com", "s.example.com", "wechat") != url_hash("https://a.com", "s.example.com", "twitter")

    def test_separator_collision_avoided(self):
        # NUL \u5206\u9694\u7b26\u9632\u6b62 "a"+\u7a7a+\u201cb\u201d \u4e0e "ab"+\u7a7a \u54c8\u5e0c\u51b2\u7a81
        h1 = url_hash("a", "b", "")
        h2 = url_hash("ab", "", "")
        assert h1 != h2

    def test_legacy_backfill_breaks_equality(self):
        # \u8fc1\u79fb\u811a\u672c\u91cc\u4f1a\u91cd\u7b97\u8001\u884c, \u8fd9\u91cc\u9a8c\u8bc1\u51fd\u6570\u672c\u8eab\u5728\u8001/\u65b0\u8c03\u7528\u65b9\u5f0f\u4e0b\u4f1a\u5f97\u5230\u4e0d\u540c\u7684\u54c8\u5e0c
        # (\u8fd9\u6b63\u662f\u8fc1\u79fb\u811a\u672c\u9700\u8981\u91cd\u7b97\u8001\u884c\u7684\u539f\u56e0)
        # 新函数 vs 老 sha256(只 hash url)不同,证明老行需要回填
        import hashlib
        legacy = hashlib.sha256(b"https://legacy.com").hexdigest()
        new = url_hash("https://legacy.com", "", "")
        assert new != legacy
        # 默认参数与显式空一致
        assert url_hash("https://legacy.com") == url_hash("https://legacy.com", "", "")


# ---------- service.create \u53bb\u91cd\u903b\u8f91 ----------

class TestServiceCreateDomainChannel:
    def test_same_url_no_domain_no_channel_dedup(self, sqlite_app):
        with sqlite_app.app_context():
            a = svc.create("https://dedup1.com")
            db.session.commit()
            b = svc.create("https://dedup1.com")
            db.session.commit()
            assert a.short_code == b.short_code

    def test_same_url_different_channel_different_code(self, sqlite_app):
        with sqlite_app.app_context():
            a = svc.create("https://multi.com", channel="wechat")
            db.session.commit()
            b = svc.create("https://multi.com", channel="twitter")
            db.session.commit()
            assert a.short_code != b.short_code

    def test_same_url_different_domain_different_code(self, sqlite_app):
        with sqlite_app.app_context():
            a = svc.create("https://multi.com", domain="s1.example.com")
            db.session.commit()
            b = svc.create("https://multi.com", domain="s2.example.com")
            db.session.commit()
            assert a.short_code != b.short_code

    def test_same_url_same_domain_same_channel_dedup(self, sqlite_app):
        with sqlite_app.app_context():
            a = svc.create("https://allmatch.com", domain="s.example.com", channel="wechat")
            db.session.commit()
            b = svc.create("https://allmatch.com", domain="s.example.com", channel="wechat")
            db.session.commit()
            assert a.short_code == b.short_code

    def test_whitespace_only_normalized_to_none(self, sqlite_app):
        with sqlite_app.app_context():
            a = svc.create("https://ws.com", domain="  ", channel="\t")
            db.session.commit()
            b = svc.create("https://ws.com")
            db.session.commit()
            # \u5168\u7a7a\u683c\u88ab\u89c4\u8303\u5316\u4e3a None,\u8ddf\u4e0d\u4f20\u57df\u540d/\u6e20\u9053 \u4e00\u81f4
            assert a.short_code == b.short_code
            assert a.domain is None
            assert a.channel is None

    def test_url_with_channel_dedup_no_domain(self, sqlite_app):
        with sqlite_app.app_context():
            a = svc.create("https://nd.com", channel="wechat")
            db.session.commit()
            b = svc.create("https://nd.com", channel="wechat")
            db.session.commit()
            assert a.short_code == b.short_code
            c = svc.create("https://nd.com", channel="app")
            db.session.commit()
            assert a.short_code != c.short_code

    def test_record_persists_domain_and_channel(self, sqlite_app):
        with sqlite_app.app_context():
            sl = svc.create("https://persist.com", domain="s.example.com", channel="wechat")
            db.session.commit()
            fetched = ShortLink.query.filter_by(short_code=sl.short_code).first()
            assert fetched.domain == "s.example.com"
            assert fetched.channel == "wechat"
            assert fetched.url_hash == url_hash("https://persist.com", "s.example.com", "wechat")


# ---------- schema \u63a5\u53d7\u65b0\u5b57\u6bb5 ----------

class TestCreateRequestSchema:
    def test_default_none(self):
        s = CreateShortLinkRequest()
        result = s.load({"long_url": "https://x.com"})
        assert result["domain"] is None
        assert result["channel"] is None
        assert result["advanced"] is None

    def test_with_domain_and_channel(self):
        s = CreateShortLinkRequest()
        result = s.load({
            "long_url": "https://x.com",
            "domain": "s.example.com",
            "channel": "wechat",
        })
        assert result["domain"] == "s.example.com"
        assert result["channel"] == "wechat"

    def test_advanced_dict_accepted(self):
        s = CreateShortLinkRequest()
        result = s.load({
            "long_url": "https://x.com",
            "advanced": {"strategy": "blacklist", "white_domain": "a.com"},
        })
        assert result["advanced"]["strategy"] == "blacklist"
        assert result["advanced"]["white_domain"] == "a.com"

    def test_domain_too_long_rejected(self):
        s = CreateShortLinkRequest()
        with pytest.raises(Exception):
            s.load({"long_url": "https://x.com", "domain": "x" * 200})

    def test_channel_too_long_rejected(self):
        s = CreateShortLinkRequest()
        with pytest.raises(Exception):
            s.load({"long_url": "https://x.com", "channel": "x" * 100})


# ---------- to_dict \u5305\u542b domain/channel ----------

class TestToDict:
    def test_to_dict_includes_domain_channel(self, sqlite_app):
        with sqlite_app.app_context():
            sl = svc.create("https://todict.com", domain="s.example.com", channel="wechat")
            db.session.commit()
            d = sl.to_dict()
            assert d["domain"] == "s.example.com"
            assert d["channel"] == "wechat"

    def test_to_dict_none_when_unset(self, sqlite_app):
        with sqlite_app.app_context():
            sl = svc.create("https://todict2.com")
            db.session.commit()
            d = sl.to_dict()
            assert d["domain"] is None
            assert d["channel"] is None
