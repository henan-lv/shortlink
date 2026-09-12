"""应用工厂:加载配置、初始化扩展、注册蓝图与路由。"""

import logging

from flask import Flask, jsonify
from sqlalchemy import text

from .config import get_config, validate_config
from .extensions import db, init_redis, ma, migrate

logger = logging.getLogger(__name__)

# flasgger 作为软依赖:缺包时仅跳过 Swagger,不影响主流程
try:
    from flasgger import Swagger
    _SWAGGER_AVAILABLE = True
except ImportError:  # pragma: no cover
    Swagger = None  # type: ignore[assignment]
    _SWAGGER_AVAILABLE = False


SWAGGER_TEMPLATE = {
    "info": {
        "title": "ShortLink API",
        "version": "1.0.0",
        "description": "短链接服务 - 生成 / 跳转 / 统计 / 链接管理 / 鉴权",
    },
    "basePath": "/",
    "schemes": ["http", "https"],
}


def create_app(config_class=None) -> Flask:
    app = Flask(__name__)

    # 1. 加载配置
    if config_class is None:
        config_class = get_config()
    cfg_instance = config_class()
    app.config.from_object(cfg_instance)
    validate_config(cfg_instance)

    # 2. 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    init_redis(app)

    # 3. Swagger(Flasgger,软依赖)
    if app.config.get("SWAGGER_ENABLED"):
        if _SWAGGER_AVAILABLE and Swagger is not None:
            Swagger(app, template=SWAGGER_TEMPLATE)
        else:
            logger.warning("flasgger 未安装,Swagger UI 已跳过(SWAGGER_ENABLED=1)")



    # 4. 注册业务蓝图
    from .api import register_blueprints
    register_blueprints(app)

    # 4.5 注册访问日志(控制台输出每个请求)
    from .middleware.access_log import register_access_log
    register_access_log(app)

    # 5. 注册 CORS(放在异常处理器之前,确保错误响应也带 CORS 头)
    from .middleware.cors import register_cors
    register_cors(app)

    # 6. 注册全局异常处理器
    from .middleware.error import register_error_handlers
    register_error_handlers(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """统一注册所有业务蓝图。后续每完成一个模块,在此追加 register_blueprint。"""
    # from .api import short_link_bp, redirect_bp, stats_bp, links_bp, auth_bp
    # app.register_blueprint(short_link_bp)
    # app.register_blueprint(redirect_bp, url_prefix="/s")
    # app.register_blueprint(stats_bp)
    # app.register_blueprint(links_bp, url_prefix="/api/links")
    # app.register_blueprint(auth_bp, url_prefix="/api/auth")
    _ = app
