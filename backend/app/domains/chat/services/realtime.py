"""Chat fan-out: per-process WebSocket registry + Redis Pub/Sub relay.

Every gunicorn worker holds only its own sockets. publish() writes the event
to Redis; each worker runs one psubscribe("chat:*") reader that relays to its
local sockets. Without REDIS_URL (dev, tests) publish() dispatches locally —
same behavior, single process only.

Channels: chat:conv:{conv_id} (thread events) and chat:admin (inbox feed —
every staff socket gets it, there is no per-agent routing yet).

WS auth is a signed 60s ticket minted over REST with the session cookie —
the socket connects cross-origin to the API host, so cookies don't ride
along on the upgrade.
"""

import asyncio
import contextlib
import json
import uuid
from typing import Literal

from fastapi import WebSocket
from itsdangerous import URLSafeTimedSerializer
from loguru import logger

from app.core.config import settings

_TICKET_MAX_AGE_S = 60
_MAX_SOCKETS_PER_USER = 5  # one customer with N tabs must not eat the fd budget

Role = Literal["customer", "admin"]


def conv_channel(conv_id: uuid.UUID) -> str:
    return f"chat:conv:{conv_id}"


def _ticket_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="chat-ws-ticket")


def issue_ws_ticket(role: Role, user_id: str) -> str:
    return _ticket_serializer().dumps({"r": role, "id": user_id})


def read_ws_ticket(ticket: str | None) -> tuple[Role, str] | None:
    if not ticket:
        return None
    try:
        data = _ticket_serializer().loads(ticket, max_age=_TICKET_MAX_AGE_S)
        return data["r"], data["id"]
    except Exception:  # noqa: BLE001 — any decode failure = no access
        return None


class ConnectionManager:
    """Local (this process) socket registry."""

    def __init__(self) -> None:
        self.by_conv: dict[uuid.UUID, set[WebSocket]] = {}
        self.admin_sockets: set[WebSocket] = set()
        self.per_user: dict[str, int] = {}

    def connect(self, ws: WebSocket, role: Role, user_id: str) -> bool:
        """Register; False if the user is over the socket cap."""
        key = f"{role}:{user_id}"
        if self.per_user.get(key, 0) >= _MAX_SOCKETS_PER_USER:
            return False
        self.per_user[key] = self.per_user.get(key, 0) + 1
        if role == "admin":
            self.admin_sockets.add(ws)
        return True

    def disconnect(self, ws: WebSocket, role: Role, user_id: str) -> None:
        key = f"{role}:{user_id}"
        n = self.per_user.get(key, 1) - 1
        if n <= 0:
            self.per_user.pop(key, None)
        else:
            self.per_user[key] = n
        self.admin_sockets.discard(ws)
        for members in self.by_conv.values():
            members.discard(ws)

    def join(self, ws: WebSocket, conv_id: uuid.UUID) -> None:
        self.by_conv.setdefault(conv_id, set()).add(ws)

    def leave(self, ws: WebSocket, conv_id: uuid.UUID) -> None:
        members = self.by_conv.get(conv_id)
        if members:
            members.discard(ws)
            if not members:
                del self.by_conv[conv_id]

    async def dispatch(self, channel: str, event: dict) -> None:
        """Deliver an event to this process's sockets for `channel`."""
        if channel == "chat:admin":
            targets = set(self.admin_sockets)
        else:
            conv_id = uuid.UUID(channel.rsplit(":", 1)[-1])
            targets = set(self.by_conv.get(conv_id, ()))
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001 — dead socket; its handler cleans up
                pass


manager = ConnectionManager()

_redis = None
_reader_task: asyncio.Task | None = None


def _client():
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def _reader() -> None:
    """One per process: relay chat:* events from Redis to local sockets."""
    while True:
        try:
            pubsub = _client().pubsub()
            await pubsub.psubscribe("chat:*")
            async for item in pubsub.listen():
                if item["type"] != "pmessage":
                    continue
                await manager.dispatch(item["channel"], json.loads(item["data"]))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — reconnect after any Redis hiccup
            logger.warning("chat pubsub reader error, reconnecting: {}", e)
            await asyncio.sleep(2)


def ensure_reader() -> None:
    """Start the relay task lazily on the first WS connection."""
    global _reader_task
    if settings.redis_url and (_reader_task is None or _reader_task.done()):
        _reader_task = asyncio.get_running_loop().create_task(_reader())


async def publish(channel: str, event: dict) -> None:
    """Fan out an event. With Redis: cross-process. Without: local only."""
    if settings.redis_url:
        try:
            await _client().publish(channel, json.dumps(event))
            return
        except Exception as e:  # noqa: BLE001 — fail open to local delivery
            logger.warning("chat publish failed, delivering locally: {}", e)
    await manager.dispatch(channel, event)


async def stop_reader() -> None:
    global _reader_task
    if _reader_task is not None:
        _reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _reader_task
        _reader_task = None
