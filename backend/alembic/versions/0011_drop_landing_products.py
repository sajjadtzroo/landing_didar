"""drop dead landing_products table

The fafbc55 refactor moved landing product assignment into `landings.content`
(JSONB groups hold ordered product ids); the `landing_products` join table has
had no reader or writer since. Migration 0007 already backfilled content from it.
Drop it. Downgrade recreates the table (empty) to match its 0003 shape.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _ts(col: str):
    return sa.Column(
        col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.drop_table("landing_products")


def downgrade() -> None:
    op.create_table(
        "landing_products",
        sa.Column(
            "landing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("landings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("landing_id", "product_id"),
    )
