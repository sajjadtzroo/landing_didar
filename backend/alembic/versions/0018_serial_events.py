"""serial_events: passport lifecycle timeline (WO 7.2)

One row per real transition on a piece (sold / revoked / restored; Phase 6 adds
warranty/buyback types). Minting is derived from product_serials.created_at and
never stored, so there is nothing to backfill.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "serial_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "serial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_serials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("meta", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_serial_events_serial_id", "serial_events", ["serial_id"])


def downgrade() -> None:
    op.drop_index("ix_serial_events_serial_id", table_name="serial_events")
    op.drop_table("serial_events")
