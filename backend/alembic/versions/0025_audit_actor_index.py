"""audit_log: index actor (admin filter would full-scan otherwise)

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-10
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_log_actor", "audit_log", ["actor"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_actor", table_name="audit_log")
