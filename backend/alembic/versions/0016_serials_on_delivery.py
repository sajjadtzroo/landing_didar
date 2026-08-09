"""serials on delivery: add order_status 'delivered' + product_serials.order_id

Delivered orders auto-mint one authenticity serial per piece, linked to the order.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG16 allows ADD VALUE inside a transaction as long as it isn't used here.
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'delivered'")
    op.add_column(
        "product_serials",
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_product_serials_order_id", "product_serials", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_product_serials_order_id", table_name="product_serials")
    op.drop_column("product_serials", "order_id")
    # Postgres can't drop an enum value — 'delivered' is left in place (harmless).
