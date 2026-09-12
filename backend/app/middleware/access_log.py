"""访问日志中间件:每次请求输出一行控制台日志。

- 跳过 OPTIONS 预检(噪音多)
- 输出:method path status duration remote_addr
"""

import logging
import time

from flask import Flask, request


def register_access_log(app: Flask) -> None:
    log = logging.getLogger("shortlink.access")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False

    @app.before_request
    def _start_timer():
        request.environ["_access_log_t0"] = time.monotonic()

    @app.after_request
    def _log_request(response):
        if request.method == "OPTIONS":
            return response
        t0 = request.environ.get("_access_log_t0")
        ms = (time.monotonic() - t0) * 1000 if t0 else 0.0
        log.info(
            "%s %s %d %.1fms %s",
            request.method,
            request.path,
            response.status_code,
            ms,
            request.headers.get("X-Forwarded-For") or request.remote_addr or "-",
        )
        return response
