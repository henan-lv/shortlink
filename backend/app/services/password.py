"""密码保护(PRD 第 5 章 F3.3)。

- 密码 6~8 位,加盐哈希存储
- Cookie 凭证,2 小时免输入
- 错误次数限制(Redis INCR + EXPIRE)
"""

import hashlib
import hmac
import time
from typing import Optional

from ..utils.hashing import hash_password as _hash, verify_password as _verify


# ---------- 密码哈希(委托 utils.hashing) ----------

def hash_password(password: str) -> str:
    return _hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _verify(password, hashed)


def validate_password_length(password: str, min_len: int = 6, max_len: int = 8) -> None:
    if not isinstance(password, str):
        raise TypeError("password 必须是字符串")
    if not (min_len <= len(password) <= max_len):
        raise ValueError(f"密码长度须在 [{min_len}, {max_len}],实际 {len(password)}")


# ---------- 凭证签名 ----------

def _sign(payload: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def issue_token(short_code: str, ttl: int, secret: str) -> str:
    """签发密码验证凭证。

    格式:{short_code}|{expires_at}|{hmac_signature}
    """
    expires_at = int(time.time()) + ttl
    payload = f"{short_code}|{expires_at}"
    sig = _sign(payload, secret)
    return f"{payload}|{sig}"


def verify_token(token: str, short_code: str, secret: str) -> bool:
    """验证凭证:签名正确、未过期、与短码匹配。"""
    try:
        sc, exp_str, sig = token.split("|")
    except ValueError:
        return False
    if sc != short_code:
        return False
    try:
        expires_at = int(exp_str)
    except ValueError:
        return False
    if expires_at < int(time.time()):
        return False
    expected = _sign(f"{sc}|{exp_str}", secret)
    return hmac.compare_digest(expected, sig)


# ---------- 错误次数限制(Redis 计数器) ----------

class PasswordAttemptLimiter:
    """按 short_code+IP+小时桶限速尝试次数。"""

    def __init__(self, redis_client, max_attempts: int = 10):
        self.redis = redis_client
        self.max_attempts = max_attempts

    def is_allowed(self, short_code: str, ip: str) -> bool:
        hour = int(time.time()) // 3600
        key = f"pw_attempt:{short_code}:{ip}:{hour}"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 3700)  # 略大于 1h,容错
        return count <= self.max_attempts
