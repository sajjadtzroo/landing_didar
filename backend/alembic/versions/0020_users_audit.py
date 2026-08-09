"""users + audit_log: RBAC foundation (WO 7.15)

Named users with roles (superadmin/operator/retailer/agent/support) and a
basic audit trail of mutating admin requests. The env-var admin keeps working
as a zero-config bootstrap superadmin outside the table.

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

admin_role = postgresql.ENUM(
    "superadmin", "operator", "retailer", "agent", "support",
    name="admin_role", create_type=False,
)


def upgrade() -> None:
    admin_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(60), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("full_name", sa.String(80)),
        sa.Column("phone", sa.String(20)),
        sa.Column("role", admin_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(60), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("status", sa.Integer()),
        sa.Column("meta", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("users")
    admin_role.drop(op.get_bind(), checkfirst=True)
