"""per-item serial codes + public authenticity verification

product_serials: one code per physical piece (1 product -> N pieces), with the
attesting spec SNAPSHOT at generation time so certificates survive product edits.
serial_scans: one row per public verify hit (copy-attack signal).

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

# Created/dropped explicitly so repeated up/down cycles don't trip on a lingering type.
# create_type=False stops create_table from ALSO emitting CREATE TYPE (double-create).
serial_status = postgresql.ENUM(
    "in_stock", "sold", "revoked", name="product_serial_status", create_type=False
)


def upgrade() -> None:
    serial_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "product_serials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(120), nullable=False),
        sa.Column("karat", sa.Integer()),
        sa.Column("weight_grams", sa.Numeric(8, 2)),
        sa.Column("image_url", sa.String(500)),
        sa.Column(
            "status", serial_status, nullable=False, server_default="in_stock"
        ),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_product_serials_code", "product_serials", ["code"], unique=True)
    op.create_index("ix_product_serials_product_id", "product_serials", ["product_id"])
    op.create_index("ix_product_serials_batch_id", "product_serials", ["batch_id"])

    op.create_table(
        "serial_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "serial_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_serials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_hash", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_serial_scans_serial_id", "serial_scans", ["serial_id"])


def downgrade() -> None:
    op.drop_table("serial_scans")
    op.drop_table("product_serials")
    serial_status.drop(op.get_bind(), checkfirst=True)
