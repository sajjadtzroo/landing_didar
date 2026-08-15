"""Customer-facing chat endpoints (mounted under /account/chat, cookie auth).
REST is both the phase-1 transport and the reconnect gap-fill path for WS."""

import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.core.limiter import limiter
from app.domains.chat.actions import ConversationAction, MessageAction
from app.domains.chat.queries import ConversationQuery, MessageQuery
from app.domains.chat.schemas import (
    ConversationOut,
    MessageIn,
    MessageOut,
    SubjectIn,
    TicketOut,
)
from app.domains.chat.services import issue_ws_ticket
from app.domains.customers import require_customer

router = APIRouter()


@router.post("/conversations", response_model=ConversationOut)
async def open_conversation(
    payload: SubjectIn,
    customer_id: uuid.UUID = Depends(require_customer),
    action: ConversationAction = Depends(),
):
    return await action.get_or_create_open(customer_id, payload.subject)


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    customer_id: uuid.UUID = Depends(require_customer),
    conversations: ConversationQuery = Depends(),
):
    return await conversations.for_customer(customer_id)


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conv_id: uuid.UUID,
    after: uuid.UUID | None = None,
    before: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
    customer_id: uuid.UUID = Depends(require_customer),
    conversations: ConversationQuery = Depends(),
    messages: MessageQuery = Depends(),
):
    await conversations.owned_or_404(conv_id, customer_id)
    return await messages.page_messages(conv_id, after, before, limit)


@router.post("/conversations/{conv_id}/messages", response_model=MessageOut)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    conv_id: uuid.UUID,
    payload: MessageIn,
    customer_id: uuid.UUID = Depends(require_customer),
    conversations: ConversationQuery = Depends(),
    action: MessageAction = Depends(),
):
    conv = await conversations.owned_or_404(conv_id, customer_id)
    return await action.send(conv, "customer", payload.content, payload.client_msg_id)


@router.post("/conversations/{conv_id}/read")
async def mark_read(
    conv_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    conversations: ConversationQuery = Depends(),
    action: ConversationAction = Depends(),
):
    conv = await conversations.owned_or_404(conv_id, customer_id)
    await action.mark_read(conv, "customer")
    return {"ok": True}


@router.post("/ws-ticket", response_model=TicketOut)
async def ws_ticket(customer_id: uuid.UUID = Depends(require_customer)):
    return TicketOut(ticket=issue_ws_ticket("customer", str(customer_id)))
