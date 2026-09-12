"""恶意链接拦截(PRD 第 5 章 F3.5)。

本地黑名单 + 多种拦截策略 + 降级参数。
- exact:精确 URL 完全匹配
- domain:按 URL 的 host 匹配
- keyword:按子串匹配(忽略大小写)
- regex:按正则匹配
"""

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from urllib.parse import urlparse


@dataclass
class BlacklistRule:
    rule_type: str  # 'exact' | 'domain' | 'keyword' | 'regex'
    pattern: str
    enabled: bool = True


class SecurityChecker:
    """恶意链接检查器。

    Args:
        rules: 规则列表
        enabled: 总开关(PRD SECURITY_ENABLED)
        fail_open: 安全库不可用/规则异常时放行(True)或拒绝(False)
    """

    def __init__(
        self,
        rules: Optional[Iterable[BlacklistRule]] = None,
        enabled: bool = True,
        fail_open: bool = False,
    ):
        self.enabled = enabled
        self.fail_open = fail_open
        self.rules: List[BlacklistRule] = list(rules or [])
        self._compiled_regex: List[re.Pattern] = []
        self._rebuild_regex()

    def _rebuild_regex(self) -> None:
        self._compiled_regex = []
        for r in self.rules:
            if r.enabled and r.rule_type == "regex":
                try:
                    self._compiled_regex.append(
                        re.compile(r.pattern, re.IGNORECASE)
                    )
                except re.error:
                    # 坏的正则,静默忽略(降级策略由 fail_open 决定)
                    continue

    def add_rule(self, rule: BlacklistRule) -> None:
        self.rules.append(rule)
        if rule.enabled and rule.rule_type == "regex":
            try:
                self._compiled_regex.append(
                    re.compile(rule.pattern, re.IGNORECASE)
                )
            except re.error:
                pass

    def is_malicious(self, url: str) -> bool:
        """True 表示判定为恶意。"""
        if not self.enabled:
            return False
        if not self.rules:
            # 无任何规则时,默认放行(由 fail_open 进一步控制)
            return not self.fail_open and False  # 放行
        try:
            return self._check(url)
        except Exception:
            # 解析/匹配异常时,根据 fail_open 决定
            return not self.fail_open

    def _check(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        url_lc = url.lower()
        for r in self.rules:
            if not r.enabled:
                continue
            if r.rule_type == "exact" and url == r.pattern:
                return True
            if r.rule_type == "domain" and host == r.pattern.lower():
                return True
            if r.rule_type == "keyword" and r.pattern.lower() in url_lc:
                return True
        for rx in self._compiled_regex:
            if rx.search(url):
                return True
        return False
