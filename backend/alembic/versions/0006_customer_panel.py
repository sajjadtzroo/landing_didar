"""add customer panel: customers, addresses, favorites, otp_codes

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-06
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _ts(col: str = "created_at"):
    return sa.Column(
        col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("full_name", sa.String(60)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=True)

    op.create_table(
        "customer_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(40), nullable=False),
        sa.Column("province", sa.String(40), nullable=False),
        sa.Column("city", sa.String(60)),
        sa.Column("line", sa.String(300), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("created_at"),
        _ts("updated_at"),
    )

    op.create_table(
        "favorites",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("customer_id", "product_id"),
    )

    op.create_table(
        "otp_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_otp_codes_phone", "otp_codes", ["phone"])


def downgrade() -> None:
    op.drop_index("ix_otp_codes_phone", "otp_codes")
    op.drop_table("otp_codes")
    op.drop_table("favorites")
    op.drop_table("customer_addresses")
    op.drop_index("ix_customers_phone", "customers")
    op.drop_table("customers")
