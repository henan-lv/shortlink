"""API 蓝图注册。"""

from . import access_rules as access_rules_module
from . import admin_users as admin_users_module
from . import auth as auth_module
from . import health as health_module
from . import links as links_module
from . import metrics as metrics_module
from . import password as password_module
from . import short_link as short_link_module
from . import stats as stats_module

ALL_BLUEPRINTS = [
    health_module.bp,
    short_link_module.bp,
    stats_module.bp,
    links_module.bp,
    auth_module.bp,
    metrics_module.bp,
    password_module.bp,
    access_rules_module.bp,
    admin_users_module.bp,
]


def register_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
