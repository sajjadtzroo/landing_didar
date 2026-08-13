"""The chat WebSocket: one socket per user, multiplexed by conv_id.

Client → server: sub / unsub {conv_id}, msg {conv_id, client_msg_id, content},
typing {conv_id}, read {conv_id}, ping.
Server → client: message, ack {client_msg_id, message}, typing, read,
conversation (status change / new thread — staff also get an inbox feed),
error, pong.

Rules that keep this safe:
- Auth is a signed 60s ticket (cookies don't cross origins on the upgrade).
- Every sub and every write re-checks ownership — a conv_id is never trusted
  just because the client claims it. Denials answer with error, not silence,
  so a buggy client fails loudly.
- One DB session per event, never held across awaits on the socket: a slow
  client must not pin a connection from the pool.
"""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select

# Module (not name) import: tests repoint core_db.SessionLocal at the test DB.
from app.core import db as core_db
from app.domains.chat import service
from app.domains.chat.models import Conversation
from app.domains.chat.realtime import ensure_reader, manager, publish, read_ws_ticket
from app.domains.chat.schemas import MessageIn, MessageOut

router = APIRouter()

_MAX_FRAME = 16 * 1024  # text frames; 4000-char messages fit with headroom


async def _authorized_conv(
    conv_id: str, role: str, user_id: str
) -> Conversation | None:
    try:
        cid = uuid.UUID(conv_id)
    except (ValueError, TypeError):
        return None
    async with core_db.SessionLocal() as db:
        conv = (
            await db.execute(select(Conversation).where(Conversation.id == cid))
        ).scalar_one_or_none()
    if conv is None:
        return None
    if role == "customer" and str(conv.customer_id) != user_id:
        return None
    return conv


@router.websocket("/chat/ws")
async def chat_ws(ws: WebSocket) -> None:
    ident = read_ws_ticket(ws.query_params.get("ticket"))
    if ident is None:
        await ws.close(code=4401)  # app-level "unauthorized"
        return
    role, user_id = ident

    await ws.accept()
    if not manager.connect(ws, role, user_id):
        await ws.close(code=4429)  # too many sockets for this user
        return
    ensure_reader()

    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > _MAX_FRAME:
                await ws.send_json({"t": "error", "detail": "frame too large"})
                continue
            try:
                frame = json.loads(raw)
                t = frame.get("t")
            except (ValueError, AttributeError):
                await ws.send_json({"t": "error", "detail": "bad frame"})
                continue

            if t == "ping":
                await ws.send_json({"t": "pong"})

            elif t in ("sub", "unsub"):
                conv = await _authorized_conv(frame.get("conv_id"), role, user_id)
                if conv is None:
                    await ws.send_json(
                        {"t": "error", "detail": "conversation not found"}
                    )
                    continue
                if t == "sub":
                    manager.join(ws, conv.id)
                else:
                    manager.leave(ws, conv.id)

            elif t == "msg":
                conv = await _authorized_conv(frame.get("conv_id"), role, user_id)
                if conv is None:
                    await ws.send_json(
                        {"t": "error", "detail": "conversation not found"}
                    )
                    continue
                try:
                    payload = MessageIn(
                        content=frame.get("content"),
                        client_msg_id=frame.get("client_msg_id"),
                    )
                except ValidationError:
                    await ws.send_json({"t": "error", "detail": "bad message"})
                    continue
                async with core_db.SessionLocal() as db:
                    db.add(conv)  # re-attach the detached row to this session
                    msg = await service.send_message(
                        db, conv, role, payload.content, payload.client_msg_id
                    )
                    await ws.send_json(
                        {
                            "t": "ack",
                            "client_msg_id": str(payload.client_msg_id)
                            if payload.client_msg_id
                            else None,
                            "message": jsonable_encoder(MessageOut.model_validate(msg)),
                        }
                    )

            elif t == "typing":
                conv = await _authorized_conv(frame.get("conv_id"), role, user_id)
                if conv is not None:
                    # Relay-only; no storage. Receivers expire it client-side.
                    await publish(
                        service.conv_channel(conv.id),
                        {"type": "typing", "conv_id": str(conv.id), "role": role},
                    )

            elif t == "read":
                conv = await _authorized_conv(frame.get("conv_id"), role, user_id)
                if conv is not None:
                    async with core_db.SessionLocal() as db:
                        db.add(conv)
                        await service.mark_read(db, conv, role)

            else:
                await ws.send_json({"t": "error", "detail": "unknown type"})

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001 — never let one socket kill the app
        logger.warning("chat ws error ({}:{}): {}", role, user_id, e)
    finally:
        manager.disconnect(ws, role, user_id)
