"""扩展实例集中管理,避免循环引用。"""

import redis
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# 数据库
db = SQLAlchemy()

# 迁移
migrate = Migrate()

# 序列化
ma = Marshmallow()

# Redis 连接池(模块级单例,在 create_app 中初始化)
_redis_pool: "redis.ConnectionPool | None" = None


def init_redis(app) -> None:
    """根据 Flask app 配置初始化 Redis 连接池。"""
    global _redis_pool
    _redis_pool = redis.ConnectionPool(
        host=app.config["REDIS_HOST"],
        port=app.config["REDIS_PORT"],
        password=app.config.get("REDIS_PASSWORD") or None,
        db=app.config["REDIS_DB"],
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        max_connections=50,
    )


def get_redis() -> "redis.Redis":
    """获取 Redis 客户端。需在 create_app 之后调用。"""
    if _redis_pool is None:
        raise RuntimeError("Redis 连接池未初始化,请先调用 init_redis(app)")
    return redis.Redis(connection_pool=_redis_pool)
