"""Staff inbox endpoints (mounted under /admin/chat). Single-agent: every
admin sees every thread; assignment/queue/transfer arrive with agent #2."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.domains.chat.actions import ConversationAction, MessageAction
from app.domains.chat.models import ConversationStatus
from app.domains.chat.queries import ConversationQuery, MessageQuery
from app.domains.chat.schemas import (
    ConversationAdminItem,
    MessageIn,
    MessageOut,
    StatusIn,
    TicketOut,
)
from app.domains.chat.services import issue_ws_ticket
from app.domains.users import require_admin

router = APIRouter()


@router.get("/chat/conversations", response_model=list[ConversationAdminItem])
async def inbox(
    status: ConversationStatus | None = None,
    limit: int = Query(default=50, le=200),
    _: str = Depends(require_admin),
    conversations: ConversationQuery = Depends(),
):
    rows = await conversations.admin_inbox(status, limit)
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
    conversations: ConversationQuery = Depends(),
    messages: MessageQuery = Depends(),
):
    await conversations.by_id_or_404(conv_id, detail="Conversation not found")
    return await messages.page_messages(conv_id, after, before, limit)


@router.post("/chat/conversations/{conv_id}/messages", response_model=MessageOut)
async def send_message(
    conv_id: uuid.UUID,
    payload: MessageIn,
    _: str = Depends(require_admin),
    conversations: ConversationQuery = Depends(),
    action: MessageAction = Depends(),
):
    conv = await conversations.by_id_or_404(conv_id, detail="Conversation not found")
    return await action.send(conv, "admin", payload.content, payload.client_msg_id)


@router.post("/chat/conversations/{conv_id}/read")
async def mark_read(
    conv_id: uuid.UUID,
    _: str = Depends(require_admin),
    conversations: ConversationQuery = Depends(),
    action: ConversationAction = Depends(),
):
    conv = await conversations.by_id_or_404(conv_id, detail="Conversation not found")
    await action.mark_read(conv, "admin")
    return {"ok": True}


@router.post("/chat/conversations/{conv_id}/status", response_model=None)
async def set_status(
    conv_id: uuid.UUID,
    payload: StatusIn,
    _: str = Depends(require_admin),
    conversations: ConversationQuery = Depends(),
    action: ConversationAction = Depends(),
):
    conv = await conversations.by_id_or_404(conv_id, detail="Conversation not found")
    await action.set_status(conv, payload.status)
    return {"ok": True}


@router.post("/chat/ws-ticket", response_model=TicketOut)
async def ws_ticket(username: str = Depends(require_admin)):
    return TicketOut(ticket=issue_ws_ticket("admin", username))
