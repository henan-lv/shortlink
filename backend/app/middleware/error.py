"""全局异常处理与业务异常类(PRD 第 11 章 HTTP 状态码)。"""

import logging
from typing import Optional

from flask import Flask

from ..utils.response import BizCode, error as error_response

logger = logging.getLogger(__name__)


# ---------- 业务异常 ----------

class BizError(Exception):
    """业务异常基类。code 与 BizCode 一致,http_status 默认与 code 相同。"""

    def __init__(self, code: int, message: str, http_status: Optional[int] = None):
        self.code = code
        self.message = message
        self.http_status = http_status if http_status is not None else code
        super().__init__(message)


class BadRequestError(BizError):
    def __init__(self, message: str = "参数错误"):
        super().__init__(BizCode.BAD_REQUEST, message)


class UnauthorizedError(BizError):
    def __init__(self, message: str = "未授权"):
        super().__init__(BizCode.UNAUTHORIZED, message)


class ForbiddenError(BizError):
    def __init__(self, message: str = "禁止访问"):
        super().__init__(BizCode.FORBIDDEN, message)


class NotFoundError(BizError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(BizCode.NOT_FOUND, message)


class ConflictError(BizError):
    def __init__(self, message: str = "冲突"):
        super().__init__(BizCode.CONFLICT, message)


class GoneError(BizError):
    """短码过期 / 软删 / 停用 (PRD 410)。"""

    def __init__(self, message: str = "资源已失效"):
        super().__init__(BizCode.GONE, message)



class ServiceUnavailableError(BizError):
    """紧急熔断 / 服务暂不可用(PRD KILL_SWITCH,HTTP 503)。"""

    def __init__(self, message: str = "服务暂不可用"):
        super().__init__(BizCode.SERVICE_UNAVAILABLE, message)


class RateLimitError(BizError):
    """触发限流(PRD 429),带 Retry-After。"""

    def __init__(self, message: str = "请求过于频繁", retry_after: int = 60):
        super().__init__(BizCode.RATE_LIMIT, message)
        self.retry_after = retry_after


# ---------- 处理器注册 ----------

def register_error_handlers(app: Flask) -> None:
    """挂载全局异常处理器,统一返回 {"code":..., "message":..., "data":...}。"""

    @app.errorhandler(BizError)
    def _handle_biz(err: BizError):
        resp, status = error_response(err.code, err.message, err.http_status)
        if isinstance(err, RateLimitError):
            resp.headers["Retry-After"] = str(err.retry_after)
        return resp, status

    @app.errorhandler(404)
    def _handle_404(_err):
        return error_response(BizCode.NOT_FOUND, "接口不存在", 404)

    @app.errorhandler(405)
    def _handle_405(_err):
        return error_response(BizCode.BAD_REQUEST, "请求方法不被允许", 405)

    try:
        from marshmallow import ValidationError as _MarshmallowValidationError

        @app.errorhandler(_MarshmallowValidationError)
        def _handle_marshmallow(err):
            messages = []
            for field, msgs in (err.messages or {}).items():
                if isinstance(msgs, dict):
                    for k, v in msgs.items():
                        joined = v if isinstance(v, str) else ", ".join(map(str, v))
                        messages.append(f"{field}.{k}: {joined}")
                else:
                    joined = msgs if isinstance(msgs, str) else ", ".join(map(str, msgs))
                    messages.append(f"{field}: {joined}")
            return error_response(
                BizCode.BAD_REQUEST,
                "; ".join(messages) if messages else "请求参数校验失败",
                400,
            )
    except ImportError:
        pass

    @app.errorhandler(Exception)
    def _handle_exception(err: Exception):
        if isinstance(err, BizError):
            return _handle_biz(err)
        logger.exception("Unhandled exception")
        return error_response(
            BizCode.SERVER_ERROR,
            "服务异常,请稍后再试",
            500,
        )
