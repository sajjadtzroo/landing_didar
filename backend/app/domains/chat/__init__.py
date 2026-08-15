"""Chat domain: live support chat between customers and shop staff
(REST + WebSocket with Redis pub/sub fan-out).

PUBLIC API — the only surface other code may import from."""

from app.domains.chat.actions import (
    ConversationAction,
    MessageAction,
    publish_conversation,
)
from app.domains.chat.models import (
    ChatMessage,
    Conversation,
    ConversationStatus,
    SenderRole,
)
from app.domains.chat.queries import ConversationQuery, MessageQuery
from app.domains.chat.schemas import (
    ConversationAdminItem,
    ConversationOut,
    MessageIn,
    MessageOut,
    StatusIn,
    SubjectIn,
    TicketOut,
)

__all__ = [
    "ChatMessage",
    "Conversation",
    "ConversationAction",
    "ConversationAdminItem",
    "ConversationOut",
    "ConversationQuery",
    "ConversationStatus",
    "MessageAction",
    "MessageIn",
    "MessageOut",
    "MessageQuery",
    "SenderRole",
    "StatusIn",
    "SubjectIn",
    "TicketOut",
    "publish_conversation",
]
