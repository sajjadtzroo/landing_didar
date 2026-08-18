"""Allow 'watch' (ساعت) as a product category.

Revision ID: 0031
Revises: 0030
Create Date: 2026-08-18
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_products_category", "products", type_="check")
    op.create_check_constraint(
        "ck_products_category",
        "products",
        "category IN ('daily', 'lux_daily', 'luxury', 'watch')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_products_category", "products", type_="check")
    op.create_check_constraint(
        "ck_products_category",
        "products",
        "category IN ('daily', 'lux_daily', 'luxury')",
    )
