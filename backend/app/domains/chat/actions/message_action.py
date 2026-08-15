import uuid
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError

from app.domains.chat.actions.conversation_action import publish_conversation
from app.domains.chat.models import ChatMessage, Conversation, ConversationStatus
from app.domains.chat.queries import MessageQuery
from app.domains.chat.schemas import MessageOut
from app.domains.chat.services import conv_channel, publish, spawn_admin_alert
from app.shared.cqrs import BaseAction


class MessageAction(BaseAction[ChatMessage]):
    model = ChatMessage

    async def send(
        self,
        conv: Conversation,
        sender_role: str,
        content: str,
        client_msg_id: uuid.UUID | None,
    ) -> ChatMessage:
        """Insert (or return the earlier insert for a retried client_msg_id),
        bump the thread, reopen if the customer writes into a settled one,
        and fan out."""
        conv_id = conv.id  # rollback expires conv; don't touch ORM attrs after it
        msg = ChatMessage(
            conversation_id=conv_id,
            sender_role=sender_role,
            content=content,
            client_msg_id=client_msg_id,
        )
        self.db.add(msg)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            return await MessageQuery(self.db).by_client_msg_id(
                conv_id, client_msg_id
            )

        conv.last_message_at = datetime.now(UTC)
        reopened = False
        if sender_role == "customer" and conv.status != ConversationStatus.open:
            conv.status = ConversationStatus.open
            reopened = True
        await self.db.commit()
        await self.db.refresh(msg)

        event = {
            "type": "message",
            "conv_id": str(conv.id),
            "message": jsonable_encoder(MessageOut.model_validate(msg)),
        }
        await publish(conv_channel(conv.id), event)
        await publish("chat:admin", event)
        if reopened:
            await publish_conversation(conv)
            spawn_admin_alert()  # a reopened thread is a new inquiry for staff
        return msg
