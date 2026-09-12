"""services.short_code 单元测试(纯算法,无外部依赖)。"""

import pytest

from app.services.short_code import (
    ShortCodeError,
    capacity,
    decode_code,
    encode_id,
    need_upgrade,
    validate_params,
)
from app.utils.base62 import decode, encode


# ---------- Base62 基础 ----------

class TestBase62:
    def test_encode_zero(self):
        assert encode(0) == "0"

    def test_encode_small(self):
        assert encode(10) == "A"          # 索引 10
        assert encode(61) == "z"          # 索引 61
        assert encode(62) == "10"         # 62 = 1*62 + 0
        assert encode(63) == "11"

    def test_encode_min_length(self):
        assert encode(1, min_length=6) == "000001"

    def test_decode_roundtrip(self):
        for n in [0, 1, 61, 62, 56800235582, 56800235583 - 1]:
            assert decode(encode(n, min_length=6)) == n

    def test_encode_negative_raises(self):
        with pytest.raises(ValueError):
            encode(-1)

    def test_decode_invalid_char(self):
        with pytest.raises(ValueError):
            decode("abc!")  # '!' 不在 Base62 字符表中


# ---------- 短码生成往返 ----------

class TestShortCodeRoundtrip:
    """ID -> 短码 -> ID 必须恒等。"""

    @pytest.mark.parametrize("length", [6, 7, 8])
    @pytest.mark.parametrize("id_", [1, 2, 100, 1_000_000, 56_800_235_582])
    def test_roundtrip(self, id_, length):
        m, b = 131, 577
        # 6 位长度容量 56,800,235,583,跳过超出用例
        if id_ > capacity(length):
            pytest.skip(f"id {id_} 超过 length={length} 容量")
        code = encode_id(id_, m, b, length)
        assert len(code) == length
        assert code.isalnum()
        assert decode_code(code, m, b, length) == id_

    def test_id1_default_params(self):
        code = encode_id(1, 131, 577, 6)
        assert len(code) == 6
        # 必须是字母数字(PRD 6.4)
        assert code.isalnum()


# ---------- 防枚举特性 ----------

class TestAntiEnumeration:
    """连续 ID 对应的短码不应连续(仿射打散效果)。"""

    def test_consecutive_ids_not_continuous(self):
        codes = [encode_id(i, 131, 577, 6) for i in range(1, 11)]
        # 任何两个连续短码前 5 位不应相同(否则视作可枚举)
        for a, b in zip(codes, codes[1:]):
            assert a[:5] != b[:5] or a == b  # 极小概率碰撞,允许极少数相等


# ---------- 参数校验 ----------

class TestValidateParams:
    def test_coprime_ok(self):
        # 131 是质数,且不被 62 整除,与 62^k 互质
        for k in [6, 7, 8]:
            validate_params(131, 577, k)  # 不抛错

    def test_multiplier_not_coprime(self):
        # 62 与 62^6 不互质
        with pytest.raises(ShortCodeError, match="不互质"):
            validate_params(62, 0, 6)

    def test_offset_out_of_range(self):
        with pytest.raises(ShortCodeError, match="越界"):
            validate_params(131, 62 ** 6, 6)

    def test_length_too_large(self):
        with pytest.raises(ShortCodeError, match="length"):
            validate_params(131, 0, 17)


# ---------- 升位策略 ----------

class TestUpgrade:
    def test_capacity(self):
        # 容量 = 62^length - 1(ID 从 1 开始,共 62^length - 1 个有效值)
        assert capacity(6) == 56_800_235_583       # 62^6 - 1
        assert capacity(7) == 3_521_614_606_207    # 62^7 - 1
        assert capacity(8) == 218_340_105_584_895  # 62^8 - 1

    def test_need_upgrade(self):
        # capacity(length) 是最大有效 ID,刚好不升位
        assert need_upgrade(capacity(6), 6) is False
        assert need_upgrade(capacity(6) + 1, 6) is True
        assert need_upgrade(capacity(6) - 1, 6) is False


# ---------- 边界与异常 ----------

class TestEdgeCases:
    def test_id_zero_raises(self):
        with pytest.raises(ShortCodeError, match="id"):
            encode_id(0, 131, 577, 6)

    def test_decode_empty(self):
        with pytest.raises(ShortCodeError):
            decode_code("", 131, 577, 6)

    def test_decode_out_of_space(self):
        # 选一个 y 值大于 6 位空间的 7 位短码(ID=10^10)
        code = encode_id(10**10, 131, 577, 7)
        assert len(code) == 7
        with pytest.raises(ShortCodeError, match="超出当前长度空间"):
            decode_code(code, 131, 577, 6)
