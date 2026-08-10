"""DB review fixes: FK indexes, buyback race constraint, string-enum CHECKs

- Postgres doesn't auto-index the FK side: order_items / order_status_log /
  customer_addresses child lookups and CASCADE deletes were full scans.
- Junction tables (favorites, agent_retailers): composite PK only covers the
  first column; index the second for reverse lookups and CASCADEs.
- One OPEN buyback per piece enforced in the DB (partial unique), killing the
  check-then-insert race on the public endpoint.
- serial_scans.created_at indexed so a future retention purge is cheap.
- CHECK constraints on string enums that gate sale/visibility logic.

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_status_log_order_id", "order_status_log", ["order_id"])
    op.create_index(
        "ix_customer_addresses_customer_id", "customer_addresses", ["customer_id"]
    )
    op.create_index("ix_favorites_product_id", "favorites", ["product_id"])
    op.create_index("ix_agent_retailers_customer_id", "agent_retailers", ["customer_id"])
    op.create_index(
        "uq_buyback_open_serial",
        "buyback_requests",
        ["serial_id"],
        unique=True,
        postgresql_where=sa.text("status = 'under_review'"),
    )
    op.create_index("ix_serial_scans_created_at", "serial_scans", ["created_at"])
    op.create_check_constraint(
        "ck_products_category", "products", "category IN ('daily', 'lux_daily', 'luxury')"
    )
    op.create_check_constraint(
        "ck_products_status",
        "products",
        "product_status IN ('sellable', 'sample', 'not_for_sale')",
    )
    op.create_check_constraint(
        "ck_gallery_kind", "mobile_gallery_items", "kind IN ('sample', 'sellable')"
    )
    op.create_check_constraint(
        "ck_gallery_status",
        "mobile_gallery_items",
        "status IN ('with_agent', 'returned', 'sold')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_gallery_status", "mobile_gallery_items")
    op.drop_constraint("ck_gallery_kind", "mobile_gallery_items")
    op.drop_constraint("ck_products_status", "products")
    op.drop_constraint("ck_products_category", "products")
    op.drop_index("ix_serial_scans_created_at", table_name="serial_scans")
    op.drop_index("uq_buyback_open_serial", table_name="buyback_requests")
    op.drop_index("ix_agent_retailers_customer_id", table_name="agent_retailers")
    op.drop_index("ix_favorites_product_id", table_name="favorites")
    op.drop_index(
        "ix_customer_addresses_customer_id", table_name="customer_addresses"
    )
    op.drop_index("ix_order_status_log_order_id", table_name="order_status_log")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
