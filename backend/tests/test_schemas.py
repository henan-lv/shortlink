"""Schemas 校验层单测。"""

import pytest

from app.schemas.short_link import (
    CreateShortLinkRequest,
    ShortLinkListQuery,
    UpdateShortLinkRequest,
    VerifyPasswordRequest,
)


class TestCreateShortLink:
    def test_valid(self):
        s = CreateShortLinkRequest()
        result = s.load({"long_url": "https://example.com"})
        assert result["long_url"] == "https://example.com"
        assert result["password"] is None
        assert result["click_limit"] is None

    def test_with_password(self):
        s = CreateShortLinkRequest()
        result = s.load({"long_url": "https://example.com", "password": "abcdef"})
        assert result["password"] == "abcdef"

    def test_with_effective_at(self):
        s = CreateShortLinkRequest()
        result = s.load({"long_url": "https://example.com", "effective_at": "2026-12-31T00:00:00"})
        assert result["effective_at"] is not None

    def test_effective_at_default_none(self):
        s = CreateShortLinkRequest()
        result = s.load({"long_url": "https://example.com"})
        assert result["effective_at"] is None

    def test_url_too_long(self):
        s = CreateShortLinkRequest()
        with pytest.raises(Exception):
            s.load({"long_url": "https://example.com/" + "a" * 2048})

    def test_password_length(self):
        s = CreateShortLinkRequest()
        with pytest.raises(Exception):
            s.load({"long_url": "https://example.com", "password": "abc"})

    def test_missing_long_url(self):
        s = CreateShortLinkRequest()
        with pytest.raises(Exception):
            s.load({})


class TestUpdateShortLink:
    def test_enabled(self):
        s = UpdateShortLinkRequest()
        assert s.load({"status": "enabled"})["status"] == "enabled"

    def test_disabled(self):
        s = UpdateShortLinkRequest()
        assert s.load({"status": "disabled"})["status"] == "disabled"

    def test_invalid_status(self):
        s = UpdateShortLinkRequest()
        with pytest.raises(Exception):
            s.load({"status": "banned"})


class TestShortLinkListQuery:
    def test_defaults(self):
        s = ShortLinkListQuery()
        result = s.load({})
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["include_deleted"] is False

    def test_page_too_large(self):
        s = ShortLinkListQuery()
        with pytest.raises(Exception):
            s.load({"page": 0})


class TestVerifyPassword:
    def test_valid(self):
        s = VerifyPasswordRequest()
        assert s.load({"password": "abcdef"})["password"] == "abcdef"

    def test_too_short(self):
        s = VerifyPasswordRequest()
        with pytest.raises(Exception):
            s.load({"password": "abc"})
