"""add customer verification fields

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_STATUS = postgresql.ENUM(
    "unverified",
    "pending",
    "approved",
    "rejected",
    name="customer_verification_status",
)


def upgrade() -> None:
    _STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column("customers", sa.Column("store_name", sa.String(80)))
    op.add_column(
        "customers",
        sa.Column(
            "verification_status",
            _STATUS,
            nullable=False,
            server_default="unverified",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "verification_documents",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("customers", sa.Column("rejection_reason", sa.String(300)))
    op.add_column("customers", sa.Column("verified_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("customers", "verified_at")
    op.drop_column("customers", "rejection_reason")
    op.drop_column("customers", "verification_documents")
    op.drop_column("customers", "verification_status")
    op.drop_column("customers", "store_name")
    _STATUS.drop(op.get_bind(), checkfirst=True)
