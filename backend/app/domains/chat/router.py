"""Customer-facing chat endpoints (mounted under /account/chat, cookie auth).
REST is both the phase-1 transport and the reconnect gap-fill path for WS."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.limiter import limiter
from app.domains.chat import service
from app.domains.chat.models import Conversation
from app.domains.chat.realtime import issue_ws_ticket
from app.domains.chat.schemas import (
    ConversationOut,
    MessageIn,
    MessageOut,
    SubjectIn,
    TicketOut,
)
from app.domains.customers import require_customer

router = APIRouter()


async def _own_conversation(
    db: AsyncSession, conv_id: uuid.UUID, customer_id: uuid.UUID
) -> Conversation:
    conv = (
        await db.execute(select(Conversation).where(Conversation.id == conv_id))
    ).scalar_one_or_none()
    # 404 for both missing and foreign threads — don't confirm existence.
    if conv is None or conv.customer_id != customer_id:
        raise HTTPException(404, detail="Conversation not found")
    return conv


@router.post("/conversations", response_model=ConversationOut)
async def open_conversation(
    payload: SubjectIn,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_or_create_open_conversation(
        db, customer_id, payload.subject
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.last_message_at.desc())
        .limit(50)
    )
    return rows.scalars().all()


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conv_id: uuid.UUID,
    after: uuid.UUID | None = None,
    before: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    await _own_conversation(db, conv_id, customer_id)
    return await service.page_messages(db, conv_id, after, before, limit)


@router.post("/conversations/{conv_id}/messages", response_model=MessageOut)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    conv_id: uuid.UUID,
    payload: MessageIn,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    conv = await _own_conversation(db, conv_id, customer_id)
    return await service.send_message(
        db, conv, "customer", payload.content, payload.client_msg_id
    )


@router.post("/conversations/{conv_id}/read")
async def mark_read(
    conv_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    conv = await _own_conversation(db, conv_id, customer_id)
    await service.mark_read(db, conv, "customer")
    return {"ok": True}


@router.post("/ws-ticket", response_model=TicketOut)
async def ws_ticket(customer_id: uuid.UUID = Depends(require_customer)):
    return TicketOut(ticket=issue_ws_ticket("customer", str(customer_id)))
