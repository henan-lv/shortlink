"""services.password 单测。"""

import time

import pytest

from app.services.password import (
    hash_password,
    issue_token,
    validate_password_length,
    verify_password,
    verify_token,
)


# ---------- 哈希 ----------

class TestPasswordHash:
    def test_hash_and_verify(self):
        h = hash_password("abcdef")
        assert h.startswith("pbkdf2_sha256$")
        assert verify_password("abcdef", h)
        assert not verify_password("wrong", h)

    def test_hash_unique_salt(self):
        a = hash_password("abcdef")
        b = hash_password("abcdef")
        assert a != b  # 不同盐

    def test_verify_invalid_format(self):
        assert verify_password("abcdef", "not-a-valid-hash") is False


# ---------- 长度校验 ----------

class TestPasswordLength:
    def test_valid_length(self):
        validate_password_length("123456", 6, 8)
        validate_password_length("12345678", 6, 8)

    @pytest.mark.parametrize("pwd", ["12345", "123456789", ""])
    def test_invalid_length(self, pwd):
        with pytest.raises(ValueError):
            validate_password_length(pwd, 6, 8)


# ---------- 凭证签发与验证 ----------

class TestToken:
    SECRET = "test-secret-key"

    def test_issue_and_verify(self):
        token = issue_token("abc123", 3600, self.SECRET)
        assert verify_token(token, "abc123", self.SECRET)

    def test_wrong_short_code(self):
        token = issue_token("abc123", 3600, self.SECRET)
        assert not verify_token(token, "xyz789", self.SECRET)

    def test_wrong_secret(self):
        token = issue_token("abc123", 3600, self.SECRET)
        assert not verify_token(token, "abc123", "different-secret")

    def test_expired(self):
        token = issue_token("abc123", -1, self.SECRET)  # 已过期
        assert not verify_token(token, "abc123", self.SECRET)

    def test_tampered_signature(self):
        token = issue_token("abc123", 3600, self.SECRET)
        tampered = token[:-2] + "ff"
        assert not verify_token(tampered, "abc123", self.SECRET)

    def test_malformed_token(self):
        for bad in ["", "a|b", "a|b|c|d", "no-pipes"]:
            assert verify_token(bad, "abc", self.SECRET) is False
