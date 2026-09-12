"""哈希工具:长链 SHA256 去重 + 密码 PBKDF2 哈希。"""

import hashlib
import hmac
import secrets

# PBKDF2 参数
_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 200_000
_PBKDF2_SALT_BYTES = 16


def url_hash(url: str, domain: str = "", channel: str = "") -> str:
    """长链 + 域名 + 渠道 SHA256 哈希值,用于强制同码去重(PRD 第 6.7 节 + 自定义域名扩展)。

    三者一起去重:同一长链 + 同一域名 + 同一渠道 → 同一短码;
    任一维度不同 → 不同短码。
    返回十六进制字符串,可作为 VARCHAR(64) 唯一索引列存储。

    分隔符用 NULL(\x00),避免 "ab"+空 与 "a"+"b"+空 的哈希冲突。
    """
    sep = "\x00"
    raw = url + sep + (domain or "") + sep + (channel or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """用 PBKDF2-HMAC-SHA256 对密码加盐哈希。"""
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """验证明文密码是否与已存储哈希匹配。"""
    try:
        algo, iters, salt_hex, digest_hex = hashed.split("$")
    except ValueError:
        return False
    if algo != f"pbkdf2_{_PBKDF2_ALGO}":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        iterations = int(iters)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO, password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(expected, actual)
