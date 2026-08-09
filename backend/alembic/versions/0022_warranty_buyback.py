"""warranty + buyback (WO 7.8 / 7.9)

warranties: one per UID (activation → expiry; status derived).
buyback_requests: UID-anchored, admin-processed (under_review/accepted/rejected).

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

buyback_status = postgresql.ENUM(
    "under_review", "accepted", "rejected", name="buyback_status", create_type=False
)


def upgrade() -> None:
    buyback_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "warranties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "serial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_serials.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("customer_name", sa.String(60)),
        sa.Column("customer_phone", sa.String(20)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "buyback_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "serial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_serials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requester_name", sa.String(60), nullable=False),
        sa.Column("requester_phone", sa.String(20), nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("status", buyback_status, nullable=False, server_default="under_review"),
        sa.Column("offered_price", sa.Numeric(14, 0)),
        sa.Column("admin_note", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_buyback_requests_serial_id", "buyback_requests", ["serial_id"])
    op.create_index("ix_buyback_requests_status", "buyback_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_buyback_requests_status", table_name="buyback_requests")
    op.drop_index("ix_buyback_requests_serial_id", table_name="buyback_requests")
    op.drop_table("buyback_requests")
    op.drop_table("warranties")
    buyback_status.drop(op.get_bind(), checkfirst=True)
