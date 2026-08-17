"""Product is_featured: curate the "پرفروش‌ترین‌ها" carousel manually
(falls back to real sales data when nothing is featured).

Revision ID: 0030
Revises: 0029
Create Date: 2026-08-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "is_featured")
