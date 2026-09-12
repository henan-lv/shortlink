"""IP 白名单(PRD 第 5 章 F3.4 P2)。

非白名单访问直接 403。CIDR 用 ipaddress 解析,
启动时一次性编译缓存,运行时只做 O(N) 遍历(N 一般很小,几十条以内)。
"""

import ipaddress
from typing import Iterable, List, Optional


class IpWhitelist:
    def __init__(self, cidrs: Optional[Iterable[str]] = None, enabled: bool = False):
        self.enabled = enabled
        self._nets: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for raw in cidrs or []:
            c = (raw or "").strip()
            if not c:
                continue
            try:
                self._nets.append(ipaddress.ip_network(c, strict=False))
            except ValueError:
                # 跳过非法 CIDR,降级到不限制
                continue

    def is_allowed(self, ip: str) -> bool:
        if not self.enabled:
            return True
        if not self._nets:
            # 启用了白名单但没有配置任何 CIDR → 全部拒绝
            return False
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        for net in self._nets:
            if addr in net:
                return True
        return False


def build_whitelist(cidrs_csv: Optional[str], enabled: bool) -> IpWhitelist:
    items = [c.strip() for c in (cidrs_csv or "").split(",") if c.strip()]
    return IpWhitelist(cidrs=items, enabled=enabled)
