"""统一 API 响应格式(PRD 第 8.4 节)。"""

from typing import Any, Optional

from flask import jsonify


def success(data: Any = None, message: str = "ok", http_status: int = 200):
    """成功响应。"""
    payload = {"code": 0, "message": message, "data": data}
    return jsonify(payload), http_status


def error(code: int, message: str, http_status: Optional[int] = None,
          data: Any = None):
    """错误响应。http_status 不传则与 code 相同。"""
    http_status = http_status if http_status is not None else code
    payload = {"code": code, "message": message, "data": data}
    return jsonify(payload), http_status


class BizCode:
    """业务错误码(与 HTTP 状态码对齐)。"""
    OK = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    GONE = 410
    RATE_LIMIT = 429
    SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
