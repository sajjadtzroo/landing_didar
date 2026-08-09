"""orders: proof of delivery (WO 7.7)

delivered_at (stamped on the transition into delivered), delivery_assignee
(agent/courier name) and delivery_proof ({photo_url?, code?, note?}). Backfills
delivered_at for orders delivered before this feature from the status log.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "orders", sa.Column("delivery_assignee", sa.String(80), nullable=True)
    )
    op.add_column("orders", sa.Column("delivery_proof", postgresql.JSONB(), nullable=True))

    # Backfill: first time each order entered `delivered`, per the status log.
    op.execute(
        """
        UPDATE orders o
        SET delivered_at = sub.first_delivered
        FROM (
            SELECT order_id, MIN(created_at) AS first_delivered
            FROM order_status_log
            WHERE to_status = 'delivered'
            GROUP BY order_id
        ) sub
        WHERE o.id = sub.order_id AND o.delivered_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("orders", "delivery_proof")
    op.drop_column("orders", "delivery_assignee")
    op.drop_column("orders", "delivered_at")
