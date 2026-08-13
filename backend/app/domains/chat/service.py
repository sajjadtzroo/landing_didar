"""Chat writes shared by REST and WS handlers: send (idempotent on
client_msg_id), read marks, status changes — each followed by its fan-out
publish so every delivery path behaves identically.
"""

import uuid
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat.models import ChatMessage, Conversation, ConversationStatus
from app.domains.chat.realtime import publish
from app.domains.chat.schemas import ConversationOut, MessageOut


def conv_channel(conv_id: uuid.UUID) -> str:
    return f"chat:conv:{conv_id}"


async def get_or_create_open_conversation(
    db: AsyncSession, customer_id: uuid.UUID, subject: str | None = None
) -> Conversation:
    """One live thread per customer; resolved/closed ones are history."""
    conv = (
        await db.execute(
            select(Conversation)
            .where(
                Conversation.customer_id == customer_id,
                Conversation.status == ConversationStatus.open,
            )
            .order_by(Conversation.created_at.desc())
        )
    ).scalar_one_or_none()
    if conv is not None:
        return conv
    conv = Conversation(customer_id=customer_id, subject=subject)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    await publish_conversation(conv)
    return conv


async def send_message(
    db: AsyncSession,
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
    db.add(msg)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return (
            await db.execute(
                select(ChatMessage).where(
                    ChatMessage.conversation_id == conv_id,
                    ChatMessage.client_msg_id == client_msg_id,
                )
            )
        ).scalar_one()

    conv.last_message_at = datetime.now(UTC)
    reopened = False
    if sender_role == "customer" and conv.status != ConversationStatus.open:
        conv.status = ConversationStatus.open
        reopened = True
    await db.commit()
    await db.refresh(msg)

    event = {
        "type": "message",
        "conv_id": str(conv.id),
        "message": jsonable_encoder(MessageOut.model_validate(msg)),
    }
    await publish(conv_channel(conv.id), event)
    await publish("chat:admin", event)
    if reopened:
        await publish_conversation(conv)
    return msg


async def page_messages(
    db: AsyncSession,
    conv_id: uuid.UUID,
    after_id: uuid.UUID | None = None,
    before_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[ChatMessage]:
    """Keyset page. after_id = reconnect gap-fill (ascending, newer than the
    anchor); before_id = history scroll (returns the window ascending too)."""
    q = select(ChatMessage).where(ChatMessage.conversation_id == conv_id)
    anchor_id = after_id or before_id
    anchor = None
    if anchor_id is not None:
        anchor = (
            await db.execute(select(ChatMessage).where(ChatMessage.id == anchor_id))
        ).scalar_one_or_none()
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
        rows = (
            (
                await db.execute(
                    q.order_by(
                        ChatMessage.created_at.desc(), ChatMessage.id.desc()
                    ).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(reversed(rows))  # …but the client always renders ascending
    rows = (
        (
            await db.execute(
                q.order_by(ChatMessage.created_at, ChatMessage.id).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def mark_read(db: AsyncSession, conv: Conversation, role: str) -> None:
    now = datetime.now(UTC)
    if role == "customer":
        conv.customer_last_read_at = now
    else:
        conv.admin_last_read_at = now
    await db.commit()
    await publish(
        conv_channel(conv.id),
        {"type": "read", "conv_id": str(conv.id), "role": role},
    )


async def publish_conversation(conv: Conversation) -> None:
    """Status/assignment changes — thread viewers and the inbox both care."""
    event = {
        "type": "conversation",
        "conv": jsonable_encoder(ConversationOut.model_validate(conv)),
    }
    await publish(conv_channel(conv.id), event)
    await publish("chat:admin", event)
