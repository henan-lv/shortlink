"""健康检查 API。"""

from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import db, get_redis

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"])
def health():
    """健康检查(DB + Redis)。"""
    result = {"status": "ok", "db": "unknown", "redis": "unknown"}
    healthy = True
    try:
        db.session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as exc:  # noqa: BLE001
        result["db"] = f"error: {exc.__class__.__name__}"
        healthy = False
    try:
        get_redis().ping()
        result["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        result["redis"] = f"error: {exc.__class__.__name__}"
        healthy = False
    result["status"] = "ok" if healthy else "degraded"
    return jsonify(result), (200 if healthy else 503)
