"""product: supplier, product_status, warrantable (WO 7.1)

Additive columns on products:
- supplier: maker/supplier (admin-only)
- product_status: sellable | sample | not_for_sale (sellability, orthogonal to
  is_active visibility). String-backed (matches `category`), validated in Pydantic.
- warrantable: whether the piece carries a warranty (Warranty module input).

server_defaults backfill existing rows to sellable / true.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("supplier", sa.String(120), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "product_status",
            sa.String(16),
            nullable=False,
            server_default="sellable",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "warrantable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "warrantable")
    op.drop_column("products", "product_status")
    op.drop_column("products", "supplier")
