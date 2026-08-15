import uuid

from fastapi import HTTPException
from sqlalchemy import Row, case, func, select

from app.domains.chat.models import ChatMessage, Conversation, ConversationStatus
from app.domains.customers import Customer
from app.shared.cqrs import BaseQuery


class ConversationQuery(BaseQuery[Conversation]):
    model = Conversation

    async def owned_or_404(
        self, conv_id: uuid.UUID, customer_id: uuid.UUID
    ) -> Conversation:
        conv = await self.by_id(conv_id)
        # 404 for both missing and foreign threads — don't confirm existence.
        if conv is None or conv.customer_id != customer_id:
            raise HTTPException(404, detail="Conversation not found")
        return conv

    async def latest_open_for_customer(
        self, customer_id: uuid.UUID
    ) -> Conversation | None:
        return await self.one_or_none(
            self.stmt()
            .where(
                Conversation.customer_id == customer_id,
                Conversation.status == ConversationStatus.open,
            )
            .order_by(Conversation.created_at.desc())
        )

    async def for_customer(
        self, customer_id: uuid.UUID, limit: int = 50
    ) -> list[Conversation]:
        return await self.all(
            self.stmt()
            .where(Conversation.customer_id == customer_id)
            .order_by(Conversation.last_message_at.desc())
            .limit(limit)
        )

    async def admin_inbox(
        self, status: ConversationStatus | None, limit: int
    ) -> list[Row]:
        """Inbox rows: (conversation, customer phone, customer name, unread
        count, last-message preview) — unread threads first."""
        unread = (
            select(func.count(ChatMessage.id))
            .where(
                ChatMessage.conversation_id == Conversation.id,
                ChatMessage.sender_role == "customer",
                ChatMessage.created_at
                > func.coalesce(
                    Conversation.admin_last_read_at, func.to_timestamp(0)
                ),
            )
            .correlate(Conversation)
            .scalar_subquery()
        )
        last_msg = (
            select(ChatMessage.content)
            .where(ChatMessage.conversation_id == Conversation.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(1)
            .correlate(Conversation)
            .scalar_subquery()
        )
        q = (
            select(Conversation, Customer.phone, Customer.full_name, unread, last_msg)
            .join(Customer, Customer.id == Conversation.customer_id)
            .order_by(
                # Unread-first so waiting customers surface above settled threads.
                case((unread > 0, 0), else_=1),
                Conversation.last_message_at.desc(),
            )
            .limit(limit)
        )
        if status is not None:
            q = q.where(Conversation.status == status)
        return list((await self.db.execute(q)).all())
