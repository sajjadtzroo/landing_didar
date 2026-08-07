"""order preferred contact method (call/agent/whatsapp)

Adds orders.contact_method. Existing rows default to 'call'.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

contact_method = sa.Enum("call", "agent", "whatsapp", name="contact_method")


def upgrade() -> None:
    contact_method.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "orders",
        sa.Column(
            "contact_method",
            contact_method,
            nullable=False,
            server_default="call",
        ),
    )
    op.alter_column("orders", "contact_method", server_default=None)


def downgrade() -> None:
    op.drop_column("orders", "contact_method")
    contact_method.drop(op.get_bind(), checkfirst=True)
