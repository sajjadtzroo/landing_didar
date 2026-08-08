"""order totals in grams: total -> Numeric(12,2), add order_items.unit_weight_grams

Wholesale gold is quantified by weight, not Toman. Order size becomes total grams;
each line snapshots its per-unit weight. Legacy unit_price/price columns stay for
old records but are no longer populated.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "orders", "total",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(14, 0),
        existing_nullable=False,
    )
    op.add_column(
        "order_items", sa.Column("unit_weight_grams", sa.Numeric(8, 2))
    )


def downgrade() -> None:
    op.drop_column("order_items", "unit_weight_grams")
    op.alter_column(
        "orders", "total",
        type_=sa.Numeric(14, 0),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=False,
    )
