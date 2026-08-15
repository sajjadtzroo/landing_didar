"""orders.phone index: /account/orders matches orders to the customer by
phone (deliberately no FK — pre-signup orders must surface after OTP login),
so the lookup was a sequential scan.

Revision ID: 0029
Revises: 0028
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_orders_phone", "orders", ["phone"])


def downgrade() -> None:
    op.drop_index("ix_orders_phone", table_name="orders")
