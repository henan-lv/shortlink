"""短码生成算法(PRD 第 6 章)。

核心流程:自增 ID → 仿射变换打散 → Base62 编码 → 短码
可逆:短码 → Base62 解码 → 仿射逆变换 → ID
"""

from math import gcd

from ..utils.base62 import decode, encode


class ShortCodeError(ValueError):
    """短码生成/解析异常。"""


def _space(length: int) -> int:
    """短码空间大小 = 62 ** length(ID 取值范围 [1, space-1],共 space-1 个)。"""
    return 62 ** length


def validate_params(multiplier: int, offset: int, length: int) -> None:
    """校验仿射参数。

    规则(PRD 6.3):
      - multiplier 必须与 62^length 互质,否则无法构成双射
      - length 须在 [1, 16] 区间(防溢出)
      - offset 须在 [0, 62^length)
    """
    if not (1 <= length <= 16):
        raise ShortCodeError(f"length 必须在 [1, 16], 实际 {length}")
    space = _space(length)
    if gcd(multiplier, space) != 1:
        raise ShortCodeError(
            f"multiplier={multiplier} 与 62^{length}={space} 不互质,无法构成双射"
        )
    if not (0 <= offset < space):
        raise ShortCodeError(f"offset={offset} 越界,需在 [0, {space})")


def capacity(length: int) -> int:
    """返回当前长度下能容纳的**最大 ID**(从 1 开始计数,共 62^length - 1 个值)。"""
    return _space(length) - 1


def encode_id(id_: int, multiplier: int, offset: int, length: int) -> str:
    """根据自增 ID 生成短码。

    仿射变换 y = (a*x + b) mod 62^length,然后 Base62 编码为 length 位字符串。
    """
    if id_ < 1:
        raise ShortCodeError(f"id 必须 >= 1, 实际 {id_}")
    if id_ > capacity(length):
        raise ShortCodeError(
            f"id={id_} 超出 length={length} 的最大容量 {capacity(length)},需升位"
        )
    validate_params(multiplier, offset, length)
    space = _space(length)
    y = (multiplier * id_ + offset) % space
    return encode(y, min_length=length)


def decode_code(code: str, multiplier: int, offset: int, length: int) -> int:
    """从短码反推 ID。

    逆变换:x = a_inv * (y - b) mod 62^length,a_inv 为 a 的模逆元。
    """
    if not code:
        raise ShortCodeError("短码不能为空")
    validate_params(multiplier, offset, length)
    space = _space(length)
    y = decode(code)
    if y >= space:
        raise ShortCodeError(
            f"短码 {code!r} 超出当前长度空间(>{space - 1})"
        )
    a_inv = pow(multiplier, -1, space)  # 扩展欧几里得求模逆元
    id_ = (a_inv * (y - offset)) % space
    # 仿射变换的像集不含 0(ID 从 1 开始),遇到 0 还原到最大 ID
    return id_ if id_ != 0 else space


def need_upgrade(id_: int, length: int) -> bool:
    """ID 是否超出当前长度容量,需要升位。"""
    return id_ > capacity(length)
