"""Flask 配置类:从 .env 加载并组装所有配置项,与 PRD 第 10 章配置项一一对应。"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 backend/.env(只加载一次,后续 os.environ.get 直接拿)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")


# ---------- 解析辅助函数 ----------

def _env(key: str, default=None):
    val = os.environ.get(key, default)
    return val if val not in (None, "") else None


def _env_str(key: str, default: str) -> str:
    val = os.environ.get(key)
    return val if val not in (None, "") else default


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val in (None, ""):
        return default
    return int(val)


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# ---------- 配置基类 ----------

class DefaultConfig:
    """默认配置,所有字段从环境变量读取,无副作用。"""

    # Flask 基础
    SECRET_KEY = _env("SECRET_KEY")  # 启动时校验,不允许为空
    FLASK_ENV = _env_str("FLASK_ENV", "production")
    FLASK_DEBUG = _env_bool("FLASK_DEBUG", False)
    DEBUG = FLASK_DEBUG
    JSON_AS_ASCII = False  # 中文响应不转义

    # JSON 排序关闭,保证字段顺序稳定
    JSON_SORT_KEYS = False

    # 应用基础
    BASE_DOMAIN = _env_str("BASE_DOMAIN", "").rstrip("/")

    # ---------- 数据库(MySQL 5.7) ----------
    DB_HOST = _env("DB_HOST")
    DB_PORT = _env_int("DB_PORT", 3306)
    DB_USER = _env("DB_USER")
    DB_PASSWORD = _env("DB_PASSWORD")
    DB_NAME = _env_str("DB_NAME", "shortlink")
    DB_CHARSET = _env_str("DB_CHARSET", "utf8mb4")
    DB_CONNECT_TIMEOUT = _env_int("DB_CONNECT_TIMEOUT", 5)

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # 防止 stale 连接
        "pool_recycle": 3600,    # MySQL wait_timeout 默认 8h,提前回收
        "pool_size": 10,
        "max_overflow": 20,
        # 连不上时快速失败:不设这个,DB 不可达会让请求一直挂着(实测挂过 118s)。
        # 注意 pymysql 的 connect_timeout 只约束 TCP connect,不约束 DNS 解析 ——
        # 域名解析失败仍然取决于系统 resolver 的超时。
        "connect_args": {"connect_timeout": DB_CONNECT_TIMEOUT},
    }

    # ---------- Redis ----------
    REDIS_HOST = _env("REDIS_HOST")
    REDIS_PORT = _env_int("REDIS_PORT", 6379)
    REDIS_PASSWORD = _env("REDIS_PASSWORD")  # 空时由 redis-py 自动忽略
    REDIS_DB = _env_int("REDIS_DB", 0)

    # ---------- 短码算法 ----------
    SHORT_CODE_MIN_LENGTH = _env_int("SHORT_CODE_MIN_LENGTH", 6)
    SHORT_CODE_MAX_LENGTH = _env_int("SHORT_CODE_MAX_LENGTH", 8)
    SHORT_CODE_AFFINE_MULTIPLIER = _env_int("SHORT_CODE_AFFINE_MULTIPLIER", 131)
    SHORT_CODE_AFFINE_OFFSET = _env_int("SHORT_CODE_AFFINE_OFFSET", 577)

    # ---------- 过期 ----------
    DEFAULT_EXPIRE_DAYS = _env_int("DEFAULT_EXPIRE_DAYS", 7)

    # ---------- 长链校验 ----------
    LONG_URL_MAX_LENGTH = _env_int("LONG_URL_MAX_LENGTH", 2048)

    # ---------- 安全 / 恶意链接拦截 ----------
    SECURITY_ENABLED = _env_bool("SECURITY_ENABLED", True)
    SECURITY_FAIL_OPEN = _env_bool("SECURITY_FAIL_OPEN", False)
    SECURITY_CHECK_ON_CREATE = _env_bool("SECURITY_CHECK_ON_CREATE", True)
    SECURITY_CHECK_ON_REDIRECT = _env_bool("SECURITY_CHECK_ON_REDIRECT", True)
    # ---------- 访问白名单 (PRD F3.4 P2) ----------
    # 仅允许配置在白名单内的 IP 段访问跳转接口,其他一律拒绝
    IP_WHITELIST_ENABLED = _env_bool("IP_WHITELIST_ENABLED", False)
    IP_WHITELIST_CIDRS = _env_str(
        "IP_WHITELIST_CIDRS",
        "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    )  # 逗号分隔 CIDR,默认放行内网

    # ---------- 反爬/防刷 (PRD F3.7 P2) ----------
    ANTI_BOT_ENABLED = _env_bool("ANTI_BOT_ENABLED", False)
    ANTI_BOT_UA_PATTERN = _env_str(
        "ANTI_BOT_UA_PATTERN",
        r"bot|crawl|spider|slurp|baidu|sogou|bingpreview|facebookexternalhit",
    )  # 命中即标记可疑(不计入 PV)
    ANTI_BOT_UA_BLOCK = _env_bool("ANTI_BOT_UA_BLOCK", False)  # True=直接 403, False=仅不计入 PV

    # ---------- 访问控制 / 风控规则 ----------
    # 跳转时按 access_rules 表(IP/CIDR/UA/Referer)判定是否拦截。
    # 规则来自:生成页「高级设置」+ 统计页「一键拦截」。
    ACCESS_CONTROL_ENABLED = _env_bool("ACCESS_CONTROL_ENABLED", True)
    # 命中拦截时返回的状态码:404=不暴露被封(推荐),403=明确告知
    ACCESS_CONTROL_BLOCK_STATUS = _env_int("ACCESS_CONTROL_BLOCK_STATUS", 404)

    # ---------- 紧急熔断 (全局开关) ----------
    # 命中后跳转接口直接返回 503,不查 DB 不写日志;日常关闭
    KILL_SWITCH_ENABLED = _env_bool("KILL_SWITCH_ENABLED", False)
    KILL_SWITCH_MESSAGE = _env_str("KILL_SWITCH_MESSAGE", "服务临时维护中,请稍后再试")


    # ---------- 限流 ----------
    RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT_PER_MINUTE = _env_int("RATE_LIMIT_PER_MINUTE", 60)
    RATE_LIMIT_RETRY_AFTER = _env_int("RATE_LIMIT_RETRY_AFTER", 60)

    # ---------- 密码保护 ----------
    PASSWORD_MIN_LENGTH = _env_int("PASSWORD_MIN_LENGTH", 6)
    PASSWORD_MAX_LENGTH = _env_int("PASSWORD_MAX_LENGTH", 8)
    PASSWORD_TOKEN_TTL = _env_int("PASSWORD_TOKEN_TTL", 7200)
    PASSWORD_MAX_ATTEMPTS = _env_int("PASSWORD_MAX_ATTEMPTS", 10)

    # ---------- Swagger ----------
    SWAGGER_ENABLED = _env_bool("SWAGGER_ENABLED", True)
    SWAGGER_PATH = _env_str("SWAGGER_PATH", "/apidocs")

    # ---------- CORS ----------
    # 逗号分隔的允许 Origin,默认覆盖本地 dev 端口
    CORS_ORIGINS = _env_str(
        "CORS_ORIGINS",
        "http://localhost:5174,http://localhost:9527,http://127.0.0.1:5174,http://127.0.0.1:9527",
    )
    CORS_ALLOW_CREDENTIALS = _env_bool("CORS_ALLOW_CREDENTIALS", True)


# ---------- 环境子类 ----------

class DevelopmentConfig(DefaultConfig):
    FLASK_DEBUG = True
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(DefaultConfig):
    FLASK_DEBUG = False
    DEBUG = False


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """根据 FLASK_ENV 选取配置类,默认 development。"""
    name = os.environ.get("FLASK_ENV", "development").lower()
    return CONFIGS.get(name, DevelopmentConfig)


# ---------- 启动校验 ----------

def validate_config(cfg: DefaultConfig) -> None:
    """关键字段缺失时直接抛错,避免运行时才暴露。"""
    missing = []
    if not cfg.SECRET_KEY:
        missing.append("SECRET_KEY")
    if not cfg.DB_HOST:
        missing.append("DB_HOST")
    if not cfg.DB_USER:
        missing.append("DB_USER")
    if cfg.DB_PASSWORD is None:
        missing.append("DB_PASSWORD")
    if not cfg.REDIS_HOST:
        missing.append("REDIS_HOST")
    if missing:
        raise RuntimeError(
            "以下必填环境变量缺失,请检查 backend/.env: " + ", ".join(missing)
        )

    # 仿射参数 sanity check(PRD 6.3:乘数需与 62^位数 互质)
    from math import gcd
    space = 62 ** cfg.SHORT_CODE_MIN_LENGTH
    if gcd(cfg.SHORT_CODE_AFFINE_MULTIPLIER, space) != 1:
        raise RuntimeError(
            f"SHORT_CODE_AFFINE_MULTIPLIER={cfg.SHORT_CODE_AFFINE_MULTIPLIER} "
            f"与 62^{cfg.SHORT_CODE_MIN_LENGTH}={space} 不互质,无法构成双射"
        )
