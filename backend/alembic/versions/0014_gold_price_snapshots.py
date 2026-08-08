"""persist last-good gold-price board so it survives restarts / TGJU outages

Single-row snapshot (id=1) upserted on every successful scrape. On a cold start
or scrape failure the service falls back to this row instead of an empty board.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-08
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gold_price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("gold_price_snapshots")
