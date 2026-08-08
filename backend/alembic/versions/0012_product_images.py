"""add product images gallery

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-08
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gallery of served media paths, populated by `python -m app.import_images`
    # from each product's MinIO folder. server_default backfills existing rows so
    # the NOT NULL column is safe to add live.
    op.add_column(
        "products",
        sa.Column(
            "images",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "images")
