"""按 IP 限流(PRD 第 5 章 F3.6)。

滑动窗口算法:Redis ZSET,score 为毫秒时间戳,member 为 uuid。
每次请求:
  1. 移除 score < now - 60s 的成员
  2. ZCARD 取当前窗口大小
  3. 超过阈值则拒绝,返回 Retry-After
  4. 否则 ZADD 本次请求,EXPIRE 自动清理
"""

import time
import uuid
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after: int  # 秒


def check_rate_limit(
    redis_client,
    ip: str,
    max_per_minute: int = 60,
    default_retry_after: int = 60,
) -> RateLimitResult:
    """检查 IP 是否触发限流。

    Args:
        redis_client: redis.Redis 实例
        ip: 客户端 IP
        max_per_minute: 每分钟阈值
        default_retry_after: 默认重试等待秒数
    """
    key = f"rl:{ip}"
    now_ms = int(time.time() * 1000)
    window_start = now_ms - 60_000

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    _, current = pipe.execute()

    if current >= max_per_minute:
        # 取最早一条记录的 score,推算需要等多久才能空出 1 个名额
        earliest = redis_client.zrange(key, 0, 0, withscores=True)
        if earliest:
            earliest_ms = int(earliest[0][1])
            wait_s = max(1, (earliest_ms + 60_000 - now_ms) // 1000)
            return RateLimitResult(False, int(wait_s))
        return RateLimitResult(False, default_retry_after)

    redis_client.zadd(key, {str(uuid.uuid4()): now_ms})
    redis_client.expire(key, 65)
    return RateLimitResult(True, 0)
