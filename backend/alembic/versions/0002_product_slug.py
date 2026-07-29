"""add product slug

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: existing rows keep NULL until reseeded; new rows always set it.
    op.add_column("products", sa.Column("slug", sa.String(80), nullable=True))
    op.create_unique_constraint("uq_products_slug", "products", ["slug"])
    op.create_index("ix_products_slug", "products", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_products_slug", "products")
    op.drop_constraint("uq_products_slug", "products", type_="unique")
    op.drop_column("products", "slug")
