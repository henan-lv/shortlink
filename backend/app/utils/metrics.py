"""轻量级 Prometheus 指标收集器。

不依赖 prometheus_client(避免引入额外依赖),手写一个最小实现:
- Counter:只增不减
- Gauge:可增可减
- Histogram:简化版(只记录总和 / 计数 / p50 / p95 / p99)

输出格式遵循 Prometheus text exposition format:
https://prometheus.io/docs/instrumenting/exposition_formats/
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List


# ---------- Counter ----------
class Counter:
    """单调递增计数器,支持 labels。"""

    def __init__(self, name: str, help: str, labelnames: List[str] | None = None):
        self.name = name
        self.help = help
        self.labelnames = labelnames or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, labels: Dict[str, str] | None = None, amount: float = 1.0) -> None:
        key = self._key(labels or {})
        with self._lock:
            self._values[key] += amount

    def _key(self, labels: Dict[str, str]) -> tuple:
        return tuple(labels.get(n, "") for n in self.labelnames)

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} counter"]
        with self._lock:
            items = sorted(self._values.items())
        for key, value in items:
            if self.labelnames:
                lbl = ",".join(f'{n}="{v}"' for n, v in zip(self.labelnames, key) if v)
                lines.append(f"{self.name}{{{lbl}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines) + "\n"


# ---------- Gauge ----------
class Gauge:
    """可增可减的瞬时值,支持 labels。"""

    def __init__(self, name: str, help: str, labelnames: List[str] | None = None):
        self.name = name
        self.help = help
        self.labelnames = labelnames or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, labels: Dict[str, str] | None = None) -> None:
        key = tuple((labels or {}).get(n, "") for n in self.labelnames)
        with self._lock:
            self._values[key] = value

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} gauge"]
        with self._lock:
            items = sorted(self._values.items())
        for key, value in items:
            if self.labelnames:
                lbl = ",".join(f'{n}="{v}"' for n, v in zip(self.labelnames, key) if v)
                lines.append(f"{self.name}{{{lbl}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines) + "\n"


# ---------- Histogram(简化版) ----------
class Histogram:
    """轻量 Histogram:只记录 count / sum / avg / max。

    Prometheus 完整版 Histogram 需要分桶,这里偷懒只暴露聚合值,
    满足 Grafana 简单监控需求。
    """

    def __init__(self, name: str, help: str, labelnames: List[str] | None = None):
        self.name = name
        self.help = help
        self.labelnames = labelnames or []
        self._stats: Dict[tuple, dict] = {}
        self._lock = threading.Lock()

    def observe(self, value: float, labels: Dict[str, str] | None = None) -> None:
        key = tuple((labels or {}).get(n, "") for n in self.labelnames)
        with self._lock:
            s = self._stats.setdefault(key, {"count": 0, "sum": 0.0, "max": 0.0})
            s["count"] += 1
            s["sum"] += value
            if value > s["max"]:
                s["max"] = value

    def render(self) -> str:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} summary"]
        with self._lock:
            items = sorted(self._stats.items())
        for key, s in items:
            avg = s["sum"] / s["count"] if s["count"] else 0
            for stat, val in [("count", s["count"]), ("sum", s["sum"]), ("avg", avg), ("max", s["max"])]:
                if self.labelnames:
                    base_lbl = ",".join(f'{n}="{v}"' for n, v in zip(self.labelnames, key) if v)
                    lbl = f"{base_lbl},stat=\"{stat}\"" if base_lbl else f"stat=\"{stat}\""
                else:
                    lbl = f"stat=\"{stat}\""
                lines.append(f"{self.name}{{{lbl}}} {val}")
        return "\n".join(lines) + "\n"


# ---------- 全局注册表 ----------
class Registry:
    """所有指标的全局容器。"""

    def __init__(self):
        self._metrics: list = []
        self._lock = threading.Lock()

    def register(self, metric) -> None:
        with self._lock:
            self._metrics.append(metric)

    def render(self) -> str:
        parts = []
        for m in self._metrics:
            parts.append(m.render())
        return "\n".join(parts)


# ---------- 全局实例 ----------
registry = Registry()

# 进程启动时间(用于 uptime 计算)
_process_start_ts = time.time()


# ---------- 业务指标 ----------
# 短链生成
shortlink_created_total = Counter(
    "shortlink_created_total",
    "累计创建的短链数量(按 domain 区分)",
    labelnames=["domain"],
)
registry.register(shortlink_created_total)

# 短链访问(按结果分类)
shortlink_redirect_total = Counter(
    "shortlink_redirect_total",
    "累计短链访问次数(按 HTTP 状态码 / 结果区分)",
    labelnames=["status"],  # ok / not_found / expired / rate_limited / malicious / needs_password
)
registry.register(shortlink_redirect_total)

# 缓存命中
shortlink_cache_total = Counter(
    "shortlink_cache_total",
    "短链缓存查询结果(命中 / 未命中)",
    labelnames=["result"],  # hit / miss
)
registry.register(shortlink_cache_total)

# 限流命中
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "累计限流命中次数(按 scope 区分)",
    labelnames=["scope"],  # global / link
)
registry.register(rate_limit_hits_total)

# HTTP 请求处理耗时
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求处理耗时(秒)",
    labelnames=["method", "endpoint"],
)
registry.register(http_request_duration_seconds)

# 当前短链总数(运行时统计,定期刷新)
shortlink_count = Gauge(
    "shortlink_count",
    "数据库中当前短链总数(enabled / total)",
    labelnames=["status"],  # enabled / disabled / total
)
registry.register(shortlink_count)


def render_metrics() -> str:
    """生成 Prometheus 文本格式输出。"""
    body = registry.render()
    # 附加进程级指标
    body += f"\n# HELP process_uptime_seconds 进程启动时长(秒)\n"
    body += f"# TYPE process_uptime_seconds gauge\n"
    body += f"process_uptime_seconds {time.time() - _process_start_ts:.2f}\n"
    return body
