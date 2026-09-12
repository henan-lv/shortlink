"""services.rate_limit 单测,使用 fake Redis mock。"""


class FakeRedis:
    """最小 Redis stub,模拟 ZSET 与 pipeline。"""

    def __init__(self):
        self.zsets: dict[str, dict[str, float]] = {}
        self.expirations: dict[str, int] = {}

    def pipeline(self):
        return _FakePipeline(self)

    def zremrangebyscore(self, key, min_, max_):
        if key not in self.zsets:
            return 0
        zs = self.zsets[key]
        removed = sum(1 for m, s in list(zs.items()) if min_ <= s <= max_)
        for m in [m for m, s in zs.items() if min_ <= s <= max_]:
            del zs[m]
        return removed

    def zcard(self, key):
        return len(self.zsets.get(key, {}))

    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)
        return len(mapping)

    def zrange(self, key, start, stop, withscores=False):
        zs = self.zsets.get(key, {})
        sorted_items = sorted(zs.items(), key=lambda x: x[1])
        sliced = sorted_items[start: stop + 1 if stop != -1 else None]
        if withscores:
            return sliced
        return [m for m, _ in sliced]

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return 1

    def incr(self, key):
        self.zsets.setdefault(key, {})
        self.zsets[key]["__counter__"] = self.zsets[key].get("__counter__", 0) + 1
        return self.zsets[key]["__counter__"]


class _FakePipeline:
    def __init__(self, redis):
        self._r = redis
        self._ops = []

    def zremrangebyscore(self, *a, **kw):
        self._ops.append(("zremrangebyscore", a, kw))
        return self

    def zcard(self, *a, **kw):
        self._ops.append(("zcard", a, kw))
        return self

    def execute(self):
        results = []
        for op, a, kw in self._ops:
            method = getattr(self._r, op)
            results.append(method(*a, **kw))
        return results


from app.services.rate_limit import check_rate_limit


class TestRateLimit:
    def setup_method(self):
        self.r = FakeRedis()

    def test_first_request_allowed(self):
        result = check_rate_limit(self.r, "1.2.3.4", max_per_minute=5)
        assert result.allowed is True
        assert result.retry_after == 0

    def test_within_limit_allowed(self):
        for _ in range(5):
            r = check_rate_limit(self.r, "1.2.3.4", max_per_minute=5)
            assert r.allowed
        # 第 6 次应拒绝
        r = check_rate_limit(self.r, "1.2.3.4", max_per_minute=5)
        assert r.allowed is False
        assert r.retry_after >= 1

    def test_separate_ips(self):
        for _ in range(5):
            check_rate_limit(self.r, "1.1.1.1", max_per_minute=5)
        # 不同 IP 不受影响
        r = check_rate_limit(self.r, "2.2.2.2", max_per_minute=5)
        assert r.allowed
