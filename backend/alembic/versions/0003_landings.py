"""add landings + landing_products

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _ts(col: str = "created_at"):
    return sa.Column(
        col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "landings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("hero_video_url", sa.String(500)),
        sa.Column("hero_poster_url", sa.String(500)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_landings_slug", "landings", ["slug"])

    op.create_table(
        "landing_products",
        sa.Column(
            "landing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("landings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("landing_id", "product_id"),
    )


def downgrade() -> None:
    op.drop_table("landing_products")
    op.drop_index("ix_landings_slug", "landings")
    op.drop_table("landings")
