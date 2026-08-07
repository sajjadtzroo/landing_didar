"""portfolios (admin-curated /shop product collections)

Adds the `portfolios` table. Each row is a named collection whose `content` JSONB
holds product groups ({title, eyebrow, description, product_ids[]}), rendered as a
section on /shop. `is_active` hides one; `sort_order` orders them.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("cover_image_url", sa.String(500)),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("content", JSONB()),
    )
    op.create_index("ix_portfolios_slug", "portfolios", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_portfolios_slug", table_name="portfolios")
    op.drop_table("portfolios")
