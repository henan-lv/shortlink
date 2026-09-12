"""Prometheus 指标端点。

GET /metrics → Prometheus 文本格式

调用一次会刷新部分 Gauge(如短链总数),其余 Counter / Histogram
由各业务模块在调用时自增。
"""

from flask import Blueprint, Response

from ..models.short_link import ShortLink, ShortLinkStatus
from ..utils.metrics import (
    render_metrics,
    shortlink_count,
)

bp = Blueprint("metrics", __name__)


def _refresh_gauges() -> None:
    """刷新 Gauge 类指标。短链数量统计。"""
    try:
        total = ShortLink.query.count()
        enabled = ShortLink.query.filter(
            ShortLink.status == ShortLinkStatus.ENABLED,
            ShortLink.is_deleted.is_(False),
        ).count()
        disabled = ShortLink.query.filter(
            ShortLink.status == ShortLinkStatus.DISABLED,
        ).count()
        malicious = ShortLink.query.filter(
            ShortLink.status == ShortLinkStatus.MALICIOUS,
        ).count()
        shortlink_count.set(total, {"status": "total"})
        shortlink_count.set(enabled, {"status": "enabled"})
        shortlink_count.set(disabled, {"status": "disabled"})
        shortlink_count.set(malicious, {"status": "malicious"})
    except Exception:  # noqa: BLE001
        # DB 暂时不可用时静默,不影响 metrics 整体响应
        pass


@bp.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus 拉取端点。"""
    _refresh_gauges()
    return Response(render_metrics(), mimetype="text/plain; version=0.0.4; charset=utf-8")
