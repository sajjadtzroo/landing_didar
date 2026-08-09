"""mobile_gallery_items: گالری سیار (WO 7.6)

A serial handed to an agent (kind: sample|sellable; status: with_agent|
returned|sold). Partial unique index: one active row per serial.

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mobile_gallery_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "serial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_serials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="with_agent"),
        sa.Column("note", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mobile_gallery_items_agent_id", "mobile_gallery_items", ["agent_id"])
    op.create_index("ix_mobile_gallery_items_serial_id", "mobile_gallery_items", ["serial_id"])
    # A piece can be in at most ONE bag at a time.
    op.create_index(
        "uq_mobile_gallery_active_serial",
        "mobile_gallery_items",
        ["serial_id"],
        unique=True,
        postgresql_where=sa.text("status = 'with_agent'"),
    )


def downgrade() -> None:
    op.drop_index("uq_mobile_gallery_active_serial", table_name="mobile_gallery_items")
    op.drop_index("ix_mobile_gallery_items_serial_id", table_name="mobile_gallery_items")
    op.drop_index("ix_mobile_gallery_items_agent_id", table_name="mobile_gallery_items")
    op.drop_table("mobile_gallery_items")
