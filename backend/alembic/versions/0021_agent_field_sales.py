"""agent field sales + B2B order workflow completion (WO 7.5 / 7.4)

- order_status gains `preparing` (در حال آماده‌سازی) — completes the WO status set.
- orders.agent_id: who placed the order on behalf of the retailer.
- agent_retailers: agent ↔ retailer (approved customer) assignment.
- agent_visits: basic field-visit notes.

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'preparing' AFTER 'confirmed'")

    op.add_column(
        "orders",
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_orders_agent_id", "orders", ["agent_id"])

    op.create_table(
        "agent_retailers",
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "agent_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_visits_agent_id", "agent_visits", ["agent_id"])
    op.create_index("ix_agent_visits_customer_id", "agent_visits", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_visits_customer_id", table_name="agent_visits")
    op.drop_index("ix_agent_visits_agent_id", table_name="agent_visits")
    op.drop_table("agent_visits")
    op.drop_table("agent_retailers")
    op.drop_index("ix_orders_agent_id", table_name="orders")
    op.drop_column("orders", "agent_id")
    # enum value `preparing` cannot be dropped from order_status; left in place
