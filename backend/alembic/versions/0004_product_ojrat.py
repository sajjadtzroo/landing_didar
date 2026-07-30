"""add product ojrat_percent

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-30
"""
import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # اجرت — making-fee %; nullable (existing rows stay NULL until set/reseeded).
    op.add_column(
        "products", sa.Column("ojrat_percent", sa.Numeric(5, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("products", "ojrat_percent")
