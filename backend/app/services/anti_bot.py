"""反爬/防刷(PRD 第 5 章 F3.7 P2)。

基于 User-Agent 关键词/正则启发;命中后:
- ANTI_BOT_UA_BLOCK=False → 不写入点击日志,跳过 PV 自增(可疑但不阻断)
- ANTI_BOT_UA_BLOCK=True  → 直接 403,等同被拦截
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class AntiBotResult:
    suspicious: bool  # True 表示 UA 命中黑名单
    blocked: bool     # True 表示需要 403


class AntiBotChecker:
    def __init__(self, ua_pattern: Optional[str] = None, enabled: bool = False, block: bool = False):
        self.enabled = enabled
        self.block = block
        self._pattern: Optional[re.Pattern] = None
        if enabled and ua_pattern:
            try:
                self._pattern = re.compile(ua_pattern, re.IGNORECASE)
            except re.error:
                self._pattern = None

    def check(self, user_agent: Optional[str]) -> AntiBotResult:
        if not self.enabled or self._pattern is None or not user_agent:
            return AntiBotResult(suspicious=False, blocked=False)
        hit = bool(self._pattern.search(user_agent))
        return AntiBotResult(suspicious=hit, blocked=hit and self.block)


def build_anti_bot(ua_pattern: Optional[str], enabled: bool, block: bool) -> AntiBotChecker:
    return AntiBotChecker(ua_pattern=ua_pattern, enabled=enabled, block=block)
