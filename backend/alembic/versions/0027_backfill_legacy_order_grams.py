"""Backfill legacy order totals from Toman to grams.

Migration 0013 changed the MEANING of orders.total (Toman -> grams) but left
pre-existing rows holding Toman prices, so the admin dashboard showed
"2,152,000,000 گرم". Recompute those rows from their items' weights.

Legacy rows are identified by total >= 1,000,000 — no real wholesale order
weighs a tonne, while every Toman price is in the millions. Items missing a
weight snapshot get one from their product's current weight; items whose
product is gone (or has no recorded weight) contribute 0. The original Toman
value survives per-item in the legacy unit_price column.

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-12
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Fill missing per-item weight snapshots from the current catalog.
    op.execute(
        """
        UPDATE order_items oi
        SET unit_weight_grams = p.weight_grams
        FROM products p
        WHERE oi.unit_weight_grams IS NULL
          AND oi.product_id = p.id
          AND p.weight_grams IS NOT NULL
        """
    )
    # 2. Recompute legacy (Toman-valued) totals as grams.
    op.execute(
        """
        UPDATE orders o
        SET total = COALESCE(sub.grams, 0)
        FROM (
            SELECT order_id,
                   SUM(COALESCE(unit_weight_grams, 0) * quantity) AS grams
            FROM order_items
            GROUP BY order_id
        ) sub
        WHERE o.id = sub.order_id
          AND o.total >= 1000000
        """
    )
    # 3. Safety net: a legacy order with no item rows at all.
    op.execute("UPDATE orders SET total = 0 WHERE total >= 1000000")


def downgrade() -> None:
    # Data fix; the overwritten Toman values are not restorable from here
    # (they remain per-item in order_items.unit_price).
    pass
