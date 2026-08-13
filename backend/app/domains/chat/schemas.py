import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domains.chat.models import ConversationStatus, SenderRole


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_msg_id: uuid.UUID | None = None


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_role: SenderRole
    content: str
    client_msg_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    status: ConversationStatus
    subject: str | None
    created_at: datetime
    last_message_at: datetime
    customer_last_read_at: datetime | None
    admin_last_read_at: datetime | None

    model_config = {"from_attributes": True}


class ConversationAdminItem(ConversationOut):
    """Inbox row: conversation + who it is + what's pending."""

    customer_id: uuid.UUID
    customer_phone: str
    customer_name: str | None
    unread: int
    last_message: str | None


class StatusIn(BaseModel):
    status: ConversationStatus


class TicketOut(BaseModel):
    ticket: str


class SubjectIn(BaseModel):
    subject: str | None = Field(default=None, max_length=200)
