"""Staff inbox endpoints (mounted under /admin/chat). Single-agent: every
admin sees every thread; assignment/queue/transfer arrive with agent #2."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.domains.chat import service
from app.domains.chat.models import ChatMessage, Conversation, ConversationStatus
from app.domains.chat.realtime import issue_ws_ticket
from app.domains.chat.schemas import (
    ConversationAdminItem,
    MessageIn,
    MessageOut,
    StatusIn,
    TicketOut,
)
from app.domains.customers import Customer
from app.domains.users import require_admin

router = APIRouter()


async def _conversation(db: AsyncSession, conv_id: uuid.UUID) -> Conversation:
    conv = (
        await db.execute(select(Conversation).where(Conversation.id == conv_id))
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(404, detail="Conversation not found")
    return conv


@router.get("/chat/conversations", response_model=list[ConversationAdminItem])
async def inbox(
    status: ConversationStatus | None = None,
    limit: int = Query(default=50, le=200),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    unread = (
        select(func.count(ChatMessage.id))
        .where(
            ChatMessage.conversation_id == Conversation.id,
            ChatMessage.sender_role == "customer",
            ChatMessage.created_at
            > func.coalesce(Conversation.admin_last_read_at, func.to_timestamp(0)),
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
    rows = (await db.execute(q)).all()
    return [
        ConversationAdminItem(
            **{
                c: getattr(conv, c)
                for c in (
                    "id",
                    "status",
                    "subject",
                    "created_at",
                    "last_message_at",
                    "customer_last_read_at",
                    "admin_last_read_at",
                    "customer_id",
                )
            },
            customer_phone=phone,
            customer_name=name,
            unread=n,
            last_message=preview,
        )
        for conv, phone, name, n, preview in rows
    ]


@router.get("/chat/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conv_id: uuid.UUID,
    after: uuid.UUID | None = None,
    before: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await _conversation(db, conv_id)
    return await service.page_messages(db, conv_id, after, before, limit)


@router.post("/chat/conversations/{conv_id}/messages", response_model=MessageOut)
async def send_message(
    conv_id: uuid.UUID,
    payload: MessageIn,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    conv = await _conversation(db, conv_id)
    return await service.send_message(
        db, conv, "admin", payload.content, payload.client_msg_id
    )


@router.post("/chat/conversations/{conv_id}/read")
async def mark_read(
    conv_id: uuid.UUID,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    conv = await _conversation(db, conv_id)
    await service.mark_read(db, conv, "admin")
    return {"ok": True}


@router.post("/chat/conversations/{conv_id}/status", response_model=None)
async def set_status(
    conv_id: uuid.UUID,
    payload: StatusIn,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    conv = await _conversation(db, conv_id)
    conv.status = payload.status
    await db.commit()
    await db.refresh(conv)
    await service.publish_conversation(conv)
    return {"ok": True}


@router.post("/chat/ws-ticket", response_model=TicketOut)
async def ws_ticket(username: str = Depends(require_admin)):
    return TicketOut(ticket=issue_ws_ticket("admin", username))
