"""add user is_admin / is_active

Revision ID: e5b9c4d2a1f3
Revises: d4e8b2c1a9f7
Create Date: 2026-09-12 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5b9c4d2a1f3'
down_revision = 'd4e8b2c1a9f7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))
    # 已有用户里最早的一位自动成为管理员,保证闭环后立即可用
    op.execute(
        "UPDATE users SET is_admin = 1 "
        "WHERE id = (SELECT id FROM (SELECT id FROM users ORDER BY id ASC LIMIT 1) AS t)"
    )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_active')
        batch_op.drop_column('is_admin')
