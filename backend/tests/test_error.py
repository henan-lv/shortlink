"""middleware.error 单测。"""

import pytest

from app.middleware.error import (
    BadRequestError,
    BizError,
    ConflictError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    register_error_handlers,
)
from app.utils.response import BizCode


# ---------- 异常类 ----------

class TestExceptions:
    def test_biz_error_defaults(self):
        e = BizError(BizCode.BAD_REQUEST, "x")
        assert e.code == BizCode.BAD_REQUEST
        assert e.message == "x"
        assert e.http_status == BizCode.BAD_REQUEST

    def test_biz_error_custom_http(self):
        e = BizError(BizCode.BAD_REQUEST, "x", http_status=400)
        assert e.http_status == 400

    def test_subclasses_codes(self):
        assert BadRequestError().code == BizCode.BAD_REQUEST
        assert UnauthorizedError().code == BizCode.UNAUTHORIZED
        assert ForbiddenError().code == BizCode.FORBIDDEN
        assert NotFoundError().code == BizCode.NOT_FOUND
        assert ConflictError().code == BizCode.CONFLICT
        assert GoneError().code == BizCode.GONE
        assert RateLimitError().code == BizCode.RATE_LIMIT

    def test_rate_limit_retry_after(self):
        e = RateLimitError(retry_after=120)
        assert e.retry_after == 120


# ---------- Flask 集成 ----------

class _DummyResponse:
    def __init__(self):
        self.headers = {}


class TestFlaskHandlers:
    """仅验证错误处理器能注册、且能处理各异常,使用最小 Flask app。"""

    @pytest.fixture
    def app(self):
        from flask import Flask, jsonify
        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.route("/raise-bad")
        def r():
            raise BadRequestError("custom bad")

        @app.route("/raise-410")
        def r2():
            raise GoneError("expired")

        @app.route("/raise-429")
        def r3():
            raise RateLimitError(retry_after=30)

        return app

    def test_register_and_biz(self, app):
        register_error_handlers(app)
        client = app.test_client()
        rv = client.get("/raise-bad")
        assert rv.status_code == 400
        body = rv.get_json()
        assert body["code"] == BizCode.BAD_REQUEST
        assert body["message"] == "custom bad"

    def test_410(self, app):
        register_error_handlers(app)
        client = app.test_client()
        rv = client.get("/raise-410")
        assert rv.status_code == 410
        assert rv.get_json()["code"] == BizCode.GONE

    def test_429_retry_after(self, app):
        register_error_handlers(app)
        client = app.test_client()
        rv = client.get("/raise-429")
        assert rv.status_code == 429
        assert rv.headers.get("Retry-After") == "30"

    def test_404(self, app):
        register_error_handlers(app)
        client = app.test_client()
        rv = client.get("/not-exists")
        assert rv.status_code == 404
        assert rv.get_json()["code"] == BizCode.NOT_FOUND
