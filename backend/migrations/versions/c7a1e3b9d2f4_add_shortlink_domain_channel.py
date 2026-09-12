"""add domain/channel to short_links + recompute url_hash for backward dedup

Revision ID: c7a1e3b9d2f4
Revises: b1f3a7d4c8e2
Create Date: 2026-09-11 16:35:00

\u53d8\u66f4:
- \u6dfb\u52a0 domain / channel \u5217(\u5747\u53ef\u7a7a,NULL \u8868\u793a\u4f7f\u7528 BASE_DOMAIN / \u65e0\u6e20\u9053)
- url_hash \u8ba1\u7b97\u53d8\u4e3a sha256(url|domain|channel)\u3002\u8001\u884c\u7684 url_hash \u53ea\u54c8\u5e0c\u4e86 url,
  \u8fc1\u79fb\u91cc\u91cd\u7b97\u4e00\u904d\u8ba9\u5b83\u4eec\u4e0e\u65b0\u63d0\u4ea4(\u7a7a\u57df\u540d+\u7a7a\u6e20\u9053)\u53e0\u52a0\u4e0a\u65b0\u54c8\u5e0c\u540e\u4ecd\u53ef\u53bb\u91cd\u3002
- \u8f6f\u5220\u7684 url_hash \u88ab\u91cd\u5199\u4e3a del-{id},\u4e0d\u53c2\u4e0e\u53bb\u91cd,\u4e0d\u9700\u8981\u91cd\u7b97\u3002
- \u589e\u52a0\u7d22\u5f15\u4ee5\u4f9b\u6309\u6e20\u9053/\u57df\u540d\u67e5\u8be2\u3002
"""

import hashlib
import os
import sys

from alembic import op
import sqlalchemy as sa


# \u8ba9 alembic \u80fd\u627e\u5230\u540e\u7aef\u6a21\u5757(\u91cd\u7b97 hash \u9700\u8981\u540c\u4e00\u4e2a\u51fd\u6570)
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.utils.hashing import url_hash  # noqa: E402


revision = 'c7a1e3b9d2f4'
down_revision = 'b1f3a7d4c8e2'
branch_labels = None
depends_on = None


def upgrade():
    # 1) \u52a0\u5217
    with op.batch_alter_table('short_links', schema=None) as batch_op:
        batch_op.add_column(sa.Column('domain', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('channel', sa.String(length=32), nullable=True))
        batch_op.create_index('idx_short_links_domain', ['domain'], unique=False)
        batch_op.create_index('idx_short_links_channel', ['channel'], unique=False)

    # 2) \u91cd\u7b97\u8001\u884c\u7684 url_hash\u3002\u8f6f\u5220\u7684\u8bb0\u5f55 url_hash \u4e3a del-{id},\u4e0d\u91cd\u7b97
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, long_url, url_hash FROM short_links WHERE url_hash NOT LIKE 'del-%'"
    )).fetchall()
    rebuilt = 0
    for r in rows:
        new_h = url_hash(r.long_url, "", "")  # \u8001\u884c\u90fd\u662f domain=NULL, channel=NULL
        if new_h != r.url_hash:
            bind.execute(
                sa.text("UPDATE short_links SET url_hash = :h WHERE id = :id"),
                {"h": new_h, "id": r.id},
            )
            rebuilt += 1
    print(f"[migration] \u91cd\u7b97 url_hash: {rebuilt} \u884c")


def downgrade():
    with op.batch_alter_table('short_links', schema=None) as batch_op:
        batch_op.drop_index('idx_short_links_channel')
        batch_op.drop_index('idx_short_links_domain')
        batch_op.drop_column('channel')
        batch_op.drop_column('domain')
    # \u4e0d\u8fd8\u539f url_hash: \u56de\u9000\u540e\u8001\u8bb0\u5f55\u4f1a\u4e0e\u65b0\u63d0\u4ea4\u51fa\u73b0\u865a\u62df\u91cd\u590d,\u4f46\u8fd9\u662f\u660e\u786e\u7684 downgrade
