"""获取客户端真实 IP(Nginx 透传)。"""

from flask import Request


def get_real_ip(req: Request) -> str:
    """按优先级获取真实 IP:

    1. X-Forwarded-For(取最左侧)
    2. X-Real-IP
    3. remote_addr
    """
    xff = req.headers.get("X-Forwarded-For", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    xri = req.headers.get("X-Real-IP", "").strip()
    if xri:
        return xri
    return req.remote_addr or "0.0.0.0"
