"""Live support chat: conversations + chat_messages.

Single-agent scope (no assignment/departments/routing yet). Read state is two
timestamps per conversation; client_msg_id unique per conversation makes
client retries idempotent at the DB layer.

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "resolved", "closed", name="conversation_status"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(200)),
        sa.Column("customer_last_read_at", sa.DateTime(timezone=True)),
        sa.Column("admin_last_read_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])
    # Admin inbox: newest-activity-first within a status tab.
    op.create_index(
        "ix_conversations_status_last_msg",
        "conversations",
        ["status", sa.text("last_message_at DESC")],
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_role",
            sa.Enum("customer", "admin", name="chat_sender_role"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("client_msg_id", UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "conversation_id", "client_msg_id", name="uq_chat_client_msg"
        ),
    )
    op.create_index(
        "ix_chat_messages_conv_created",
        "chat_messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("conversations")
    sa.Enum(name="chat_sender_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="conversation_status").drop(op.get_bind(), checkfirst=True)
