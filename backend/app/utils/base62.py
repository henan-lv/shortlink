"""Base62 编码/解码,用于短码生成(PRD 第 6.4 节)。

字符表:数字 0-9、大写 A-Z、小写 a-z,共 62 个,顺序固定。
"""

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE = len(BASE62_ALPHABET)
_DECODE_MAP = {ch: i for i, ch in enumerate(BASE62_ALPHABET)}


def encode(n: int, min_length: int = 0) -> str:
    """把非负整数编码为 Base62 字符串。

    参数:
        n: 非负整数
        min_length: 最小长度,不足时左补 '0'
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if n == 0:
        return "0" * max(1, min_length)
    chars = []
    while n > 0:
        n, rem = divmod(n, _BASE)
        chars.append(BASE62_ALPHABET[rem])
    s = "".join(reversed(chars))
    if min_length and len(s) < min_length:
        s = s.rjust(min_length, "0")
    return s


def decode(s: str) -> int:
    """把 Base62 字符串解码为非负整数。非法字符抛 ValueError。"""
    if not s:
        raise ValueError("empty string")
    n = 0
    for ch in s:
        v = _DECODE_MAP.get(ch)
        if v is None:
            raise ValueError(f"invalid Base62 character: {ch!r}")
        n = n * _BASE + v
    return n
