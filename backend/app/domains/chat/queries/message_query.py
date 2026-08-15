import uuid

from sqlalchemy import tuple_

from app.domains.chat.models import ChatMessage
from app.shared.cqrs import BaseQuery


class MessageQuery(BaseQuery[ChatMessage]):
    model = ChatMessage

    async def by_client_msg_id(
        self, conv_id: uuid.UUID, client_msg_id: uuid.UUID
    ) -> ChatMessage:
        return (
            await self.db.execute(
                self.stmt().where(
                    ChatMessage.conversation_id == conv_id,
                    ChatMessage.client_msg_id == client_msg_id,
                )
            )
        ).scalar_one()

    async def page_messages(
        self,
        conv_id: uuid.UUID,
        after_id: uuid.UUID | None = None,
        before_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """Keyset page. after_id = reconnect gap-fill (ascending, newer than the
        anchor); before_id = history scroll (returns the window ascending too).
        NOTE: documented limit goes to 200 (> MAX_PAGE_SIZE), so this keeps its
        own limit handling instead of BaseQuery.page()."""
        q = self.stmt().where(ChatMessage.conversation_id == conv_id)
        anchor_id = after_id or before_id
        anchor = None
        if anchor_id is not None:
            anchor = await self.one_or_none(
                self.stmt().where(ChatMessage.id == anchor_id)
            )
        if anchor is not None and after_id is not None:
            q = q.where(
                tuple_(ChatMessage.created_at, ChatMessage.id)
                > tuple_(anchor.created_at, anchor.id)
            )
        if anchor is not None and before_id is not None:
            q = q.where(
                tuple_(ChatMessage.created_at, ChatMessage.id)
                < tuple_(anchor.created_at, anchor.id)
            )
        if before_id is not None or after_id is None:
            # history scroll and "latest window" both read newest-first…
            rows = await self.all(
                q.order_by(
                    ChatMessage.created_at.desc(), ChatMessage.id.desc()
                ).limit(limit)
            )
            return list(reversed(rows))  # …but the client always renders ascending
        return await self.all(
            q.order_by(ChatMessage.created_at, ChatMessage.id).limit(limit)
        )
