"""Add site_settings singleton table for admin-controlled feature flags.

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "data",
            JSONB(),
            nullable=False,
            server_default='{"price_requires_login": false}',
        ),
    )
    # Seed the singleton row so GET never 404s before the first admin PATCH.
    op.execute(
        "INSERT INTO site_settings (id, data) "
        "VALUES (1, '{\"price_requires_login\": false}'::jsonb) "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("site_settings")
