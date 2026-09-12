"""密码验证 API(跳转前给 Cookie 凭证,2 小时免输入)。"""

from flask import Blueprint, current_app, g, make_response, request

from ..extensions import get_redis
from ..middleware.error import (
    BadRequestError,
    GoneError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
)
from ..schemas.short_link import VerifyPasswordRequest
from ..services import password as password_service
from ..services import short_link as svc
from ..services.rate_limit import check_rate_limit
from ..utils.ip import get_real_ip
from ..utils.response import success

bp = Blueprint("password", __name__)


@bp.route("/api/shortlinks/<short_code>/verify-password", methods=["POST"])
def verify_password(short_code):
    """密码验证,通过后下发 Cookie 凭证(2 小时有效)。"""
    payload = VerifyPasswordRequest().load(request.get_json(silent=True) or {})
    sl = svc.get_active_by_code(short_code)
    if sl is None or not sl.password_hash:
        raise NotFoundError("短码不存在或未启用密码")

    outcome, _ = svc.redirect_pre_check(sl)
    if outcome == svc.RedirectOutcome.GONE:
        raise GoneError("短链已失效")
    if outcome == svc.RedirectOutcome.MALICIOUS:
        raise BadRequestError("链接已失效")

    cfg = current_app.config
    ip = get_real_ip(request)
    if cfg.get("RATE_LIMIT_ENABLED"):
        result = check_rate_limit(
            get_redis(), ip,
            max_per_minute=cfg["RATE_LIMIT_PER_MINUTE"],
            default_retry_after=cfg["RATE_LIMIT_RETRY_AFTER"],
        )
        if not result.allowed:
            raise RateLimitError("请求过于频繁", retry_after=result.retry_after)

    # 错误次数限制
    from ..services.password import PasswordAttemptLimiter
    limiter = PasswordAttemptLimiter(get_redis(), cfg["PASSWORD_MAX_ATTEMPTS"])
    if not limiter.is_allowed(short_code, ip):
        raise RateLimitError("尝试次数过多,请稍后再试", retry_after=3600)

    if not password_service.verify_password(payload["password"], sl.password_hash):
        raise UnauthorizedError("密码错误")

    token = password_service.issue_token(
        short_code, cfg["PASSWORD_TOKEN_TTL"], cfg["SECRET_KEY"]
    )
    resp = make_response(success({"verified": True, "ttl": cfg["PASSWORD_TOKEN_TTL"]}))
    resp.set_cookie(
        f"pw_{short_code}", token,
        max_age=cfg["PASSWORD_TOKEN_TTL"], httponly=True, samesite="Lax",
    )
    return resp
