"""CORS 中间件:用 after_request 手动加跨域头。

不引入 flask-cors 依赖,逻辑简单可控。
- OPTIONS 预检由 catch-all 路由直接 204 返回;
- after_request 统一回写 Access-Control-Allow-* 头。
"""

import logging
from typing import Iterable, List

from flask import Flask, request

logger = logging.getLogger(__name__)


def _parse_origins(raw: str) -> List[str]:
    return [o.strip() for o in (raw or "").split(",") if o.strip()]


def _resolve_allowed(origin: str, allowlist: Iterable[str]) -> str | None:
    if not origin:
        return None
    if "*" in allowlist:
        return "*"
    return origin if origin in allowlist else None


def register_cors(app: Flask) -> None:
    cfg = app.config
    allowlist = _parse_origins(cfg.get("CORS_ORIGINS", ""))
    allow_credentials = bool(cfg.get("CORS_ALLOW_CREDENTIALS", True))

    @app.after_request
    def _set_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed = _resolve_allowed(origin, allowlist) if origin else None

        if allowed:
            response.headers["Access-Control-Allow-Origin"] = allowed
            response.headers["Vary"] = "Origin"
            if allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With"
            )
            response.headers["Access-Control-Max-Age"] = "3600"

        return response

    # catch-all OPTIONS:任何路径的预检都直接 204
    @app.route("/", defaults={"_path": ""}, methods=["OPTIONS"])
    @app.route("/<path:_path>", methods=["OPTIONS"])
    def _cors_preflight(_path=""):
        return ("", 204)

    logger.info("CORS 已启用,允许 Origin: %s", allowlist)
