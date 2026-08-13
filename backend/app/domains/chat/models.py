"""Live support chat: one conversation thread per customer episode, messages
between the customer and shop staff (single-agent today — no assignment,
departments or routing; see docs/architecture/support-chat.md for the shape
those grow into).

Read state is two timestamps on the conversation (per side), not per-message
status rows: unread = messages from the other side newer than my mark.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ConversationStatus(enum.StrEnum):
    open = "open"
    resolved = "resolved"
    closed = "closed"


class SenderRole(enum.StrEnum):
    customer = "customer"
    admin = "admin"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.open,
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String(200))
    customer_last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    admin_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # created_at / updated_at come from Base
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        # Client retries after a dropped socket resend the same client_msg_id;
        # the DB, not the handler, guarantees they land once.
        UniqueConstraint("conversation_id", "client_msg_id", name="uq_chat_client_msg"),
        # Keyset paging within a thread.
        Index("ix_chat_messages_conv_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_role: Mapped[SenderRole] = mapped_column(
        SAEnum(SenderRole, name="chat_sender_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_msg_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # created_at / updated_at come from Base
