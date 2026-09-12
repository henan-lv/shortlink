"""创建/重置管理员账号。

用法:
    python scripts/create_admin.py                       # 默认 admin / admin123
    python scripts/create_admin.py --username root       # 自定义用户名
    python scripts/create_admin.py --password s3cret     # 自定义密码
    python scripts/create_admin.py --reset               # 已存在则重置密码

账号已存在时默认跳过;加 --reset 会重置密码。
"""

import argparse
import sys
from pathlib import Path

# 让脚本能 import app 包
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402
from app.services import auth as auth_service  # noqa: E402
from app.services import password as password_service  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="创建/重置管理员账号")
    parser.add_argument("--username", default="admin", help="用户名(默认 admin)")
    parser.add_argument("--password", default="admin123", help="密码(默认 admin123)")
    parser.add_argument("--reset", action="store_true", help="账号已存在时重置密码")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        existing = auth_service.get_by_username(args.username)
        if existing and not args.reset:
            print(f"账号已存在: id={existing.id} username={existing.username!r} (传 --reset 可重置密码)")
            return 0
        if existing:
            existing.password_hash = password_service.hash_password(args.password)
            db.session.commit()
            print(f"已重置密码: id={existing.id} username={existing.username!r}")
            return 0
        # 复用 service.register 的校验,失败抛 BadRequestError 直接报错
        try:
            user = auth_service.register(args.username, args.password)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"创建失败: {e}", file=sys.stderr)
            return 1
        print(f"创建成功: id={user.id} username={user.username!r} api_key={user.api_key}")
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
