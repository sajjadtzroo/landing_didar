"""Conversation writes shared by REST and WS handlers: open (get-or-create),
read marks, status changes — each followed by its fan-out publish so every
delivery path behaves identically.
"""

import uuid
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder

from app.domains.chat.models import Conversation, ConversationStatus
from app.domains.chat.queries import ConversationQuery
from app.domains.chat.schemas import ConversationOut
from app.domains.chat.services import conv_channel, publish, spawn_admin_alert
from app.shared.cqrs import BaseAction


async def publish_conversation(conv: Conversation) -> None:
    """Status/assignment changes — thread viewers and the inbox both care."""
    event = {
        "type": "conversation",
        "conv": jsonable_encoder(ConversationOut.model_validate(conv)),
    }
    await publish(conv_channel(conv.id), event)
    await publish("chat:admin", event)


class ConversationAction(BaseAction[Conversation]):
    model = Conversation

    async def get_or_create_open(
        self, customer_id: uuid.UUID, subject: str | None = None
    ) -> Conversation:
        """One live thread per customer; resolved/closed ones are history."""
        conv = await ConversationQuery(self.db).latest_open_for_customer(customer_id)
        if conv is not None:
            return conv
        conv = await self.save(Conversation(customer_id=customer_id, subject=subject))
        await publish_conversation(conv)
        spawn_admin_alert()
        return conv

    async def mark_read(self, conv: Conversation, role: str) -> None:
        now = datetime.now(UTC)
        if role == "customer":
            conv.customer_last_read_at = now
        else:
            conv.admin_last_read_at = now
        await self.db.commit()
        await publish(
            conv_channel(conv.id),
            {"type": "read", "conv_id": str(conv.id), "role": role},
        )

    async def set_status(
        self, conv: Conversation, status: ConversationStatus
    ) -> Conversation:
        conv.status = status
        await self.commit_and_refresh(conv)
        await publish_conversation(conv)
        return conv
