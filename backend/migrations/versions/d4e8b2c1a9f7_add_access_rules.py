"""add access_rules table for access control / risk rules

Revision ID: d4e8b2c1a9f7
Revises: c7a1e3b9d2f4
Create Date: 2026-09-11 17:20:00

变更:
- 新增 access_rules 表:访问控制(风控)规则
  - rule_type: ip / ip_cidr / ua / referer
  - mode: block(黑名单) / allow(白名单)
  - action: block(拒绝) / observe(仅观察计数)
  - scope: short_code(单链) / global(该用户全部短链)
  - source: advanced(生成页高级设置) / manual(统计页一键拦截) / auto(预留)
  - expire_at: 为空表示永久;临时封禁应设置
- 规则在跳转链路上执行;被拦截的请求不写 click_logs,仅记 Redis 计数
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e8b2c1a9f7'
down_revision = 'c7a1e3b9d2f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'access_rules',
        sa.Column(
            'id',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('rule_type', sa.String(length=16), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('mode', sa.String(length=16), nullable=False),
        sa.Column('action', sa.String(length=16), nullable=False),
        sa.Column('scope', sa.String(length=16), nullable=False),
        sa.Column('short_code', sa.String(length=16), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('expire_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('access_rules', schema=None) as batch_op:
        batch_op.create_index('idx_access_rules_code_enabled', ['short_code', 'enabled'], unique=False)
        batch_op.create_index('idx_access_rules_scope_enabled', ['scope', 'enabled'], unique=False)
        batch_op.create_index('idx_access_rules_expire', ['expire_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_access_rules_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_access_rules_short_code'), ['short_code'], unique=False)


def downgrade():
    with op.batch_alter_table('access_rules', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_access_rules_short_code'))
        batch_op.drop_index(batch_op.f('ix_access_rules_user_id'))
        batch_op.drop_index('idx_access_rules_expire')
        batch_op.drop_index('idx_access_rules_scope_enabled')
        batch_op.drop_index('idx_access_rules_code_enabled')

    op.drop_table('access_rules')
