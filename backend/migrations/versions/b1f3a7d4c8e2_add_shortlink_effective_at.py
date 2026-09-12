"""add effective_at to short_links

Revision ID: b1f3a7d4c8e2
Revises: a9f2fc5aea29
Create Date: 2026-09-11 02:39:58
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1f3a7d4c8e2'
down_revision = 'a9f2fc5aea29'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('short_links', schema=None) as batch_op:
        batch_op.add_column(sa.Column('effective_at', sa.DateTime(), nullable=True))
        batch_op.create_index('idx_short_links_effective', ['effective_at'], unique=False)


def downgrade():
    with op.batch_alter_table('short_links', schema=None) as batch_op:
        batch_op.drop_index('idx_short_links_effective')
        batch_op.drop_column('effective_at')
