"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-29
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# create_type=False: we create/drop the type explicitly below, so the table
# DDL must NOT also emit CREATE TYPE (that would fail: type already exists).
order_status = postgresql.ENUM(
    "new",
    "contacted",
    "confirmed",
    "shipped",
    "cancelled",
    name="order_status",
    create_type=False,
)


def _ts(col: str = "created_at"):
    return sa.Column(
        col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sku", sa.String(40), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("weight_grams", sa.Numeric(8, 2)),
        sa.Column("karat", sa.Integer()),
        sa.Column("price", sa.Numeric(12, 0)),
        sa.Column("image_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
    )

    op.create_table(
        "faqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
    )

    order_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reference", sa.String(16), nullable=False, unique=True),
        sa.Column("full_name", sa.String(60), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("store_name", sa.String(80), nullable=False),
        sa.Column("province", sa.String(40), nullable=False),
        sa.Column("city", sa.String(60)),
        sa.Column("note", sa.String(300)),
        sa.Column("internal_note", sa.String(1000)),
        sa.Column("status", order_status, nullable=False, server_default="new"),
        sa.Column("total", sa.Numeric(14, 0), nullable=False, server_default="0"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(64), unique=True),
        sa.Column("utm_source", sa.String(120)),
        sa.Column("utm_medium", sa.String(120)),
        sa.Column("utm_campaign", sa.String(120)),
        sa.Column("referrer", sa.String(500)),
        sa.Column("ip_hash", sa.String(64)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_province", "orders", ["province"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
        ),
        sa.Column("product_name", sa.String(120), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 0)),
        sa.Column("quantity", sa.Integer(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
    )

    op.create_table(
        "order_status_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", order_status),
        sa.Column("to_status", order_status, nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
    )


def downgrade() -> None:
    op.drop_table("order_status_log")
    op.drop_table("order_items")
    op.drop_index("ix_orders_province", "orders")
    op.drop_index("ix_orders_status", "orders")
    op.drop_index("ix_orders_created_at", "orders")
    op.drop_table("orders")
    op.drop_table("faqs")
    op.drop_table("products")
    order_status.drop(op.get_bind(), checkfirst=True)
