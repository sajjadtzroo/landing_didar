"""add product category

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-30
"""
import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # "daily" | "luxury" — landing carousel grouping. server_default backfills
    # existing rows so the NOT NULL column is safe to add live.
    op.add_column(
        "products",
        sa.Column("category", sa.String(20), nullable=False, server_default="daily"),
    )


def downgrade() -> None:
    op.drop_column("products", "category")
