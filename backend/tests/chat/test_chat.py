"""Support chat: REST flow, authorization boundaries, retry idempotency,
WS ticket + connection-manager units. The full socket loop is exercised
against the running stack (it needs real upgrade semantics), not here.
"""

import uuid

import pytest

from app.domains.chat.routers.ws import _authorized_conv
from app.domains.chat.services.realtime import (
    ConnectionManager,
    issue_ws_ticket,
    read_ws_ticket,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

ACC = "/api/v1/account"
CHAT = "/api/v1/account/chat"
ADMIN = "/api/v1/admin/chat"


async def _login(client, phone="09121234567"):
    r = await client.post(f"{ACC}/otp/request", json={"phone": phone})
    assert r.status_code == 200, r.text
    r = await client.post(
        f"{ACC}/otp/verify", json={"phone": phone, "code": r.json()["dev_code"]}
    )
    assert r.status_code == 200, r.text
    return r.json()


async def _open_conv(client) -> dict:
    r = await client.post(f"{CHAT}/conversations", json={})
    assert r.status_code == 200, r.text
    return r.json()


# ---- Customer REST flow ----


async def test_open_conversation_is_get_or_create(client):
    await _login(client)
    a = await _open_conv(client)
    b = await _open_conv(client)
    assert a["id"] == b["id"]  # one live thread per customer
    assert a["status"] == "open"


async def test_send_and_list_messages(client):
    await _login(client)
    conv = await _open_conv(client)
    r = await client.post(
        f"{CHAT}/conversations/{conv['id']}/messages", json={"content": "سلام"}
    )
    assert r.status_code == 200, r.text
    msg = r.json()
    assert msg["sender_role"] == "customer"

    r = await client.get(f"{CHAT}/conversations/{conv['id']}/messages")
    assert [m["id"] for m in r.json()] == [msg["id"]]

    # after= gap-fill returns only what came later
    r2 = await client.post(
        f"{CHAT}/conversations/{conv['id']}/messages", json={"content": "دوم"}
    )
    r = await client.get(
        f"{CHAT}/conversations/{conv['id']}/messages", params={"after": msg["id"]}
    )
    assert [m["id"] for m in r.json()] == [r2.json()["id"]]


async def test_client_msg_id_retry_is_idempotent(client):
    await _login(client)
    conv = await _open_conv(client)
    cmid = str(uuid.uuid4())
    body = {"content": "retry me", "client_msg_id": cmid}
    a = await client.post(f"{CHAT}/conversations/{conv['id']}/messages", json=body)
    b = await client.post(f"{CHAT}/conversations/{conv['id']}/messages", json=body)
    assert a.json()["id"] == b.json()["id"]
    r = await client.get(f"{CHAT}/conversations/{conv['id']}/messages")
    assert len(r.json()) == 1


async def test_foreign_conversation_is_404(client, admin_client):
    await _login(client, phone="09121111111")
    conv = await _open_conv(client)

    # log in as a different customer on the same client (cookie replaced)
    await _login(client, phone="09122222222")
    for method, path, body in [
        ("get", f"{CHAT}/conversations/{conv['id']}/messages", None),
        ("post", f"{CHAT}/conversations/{conv['id']}/messages", {"content": "x"}),
        ("post", f"{CHAT}/conversations/{conv['id']}/read", None),
    ]:
        r = await getattr(client, method)(
            path, **({"json": body} if body is not None else {})
        )
        assert r.status_code == 404, f"{method} {path} -> {r.status_code}"


# ---- Admin flow ----


async def test_admin_inbox_unread_and_read_cycle(client, admin_client):
    await _login(client)
    conv = await _open_conv(client)
    await client.post(
        f"{CHAT}/conversations/{conv['id']}/messages", json={"content": "کمک"}
    )

    r = await admin_client.get(f"{ADMIN}/conversations")
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["unread"] == 1
    assert items[0]["last_message"] == "کمک"
    assert items[0]["customer_phone"] == "09121234567"

    await admin_client.post(f"{ADMIN}/conversations/{conv['id']}/read")
    r = await admin_client.get(f"{ADMIN}/conversations")
    assert r.json()[0]["unread"] == 0


async def test_admin_reply_and_customer_sees_it(client, admin_client):
    await _login(client)
    conv = await _open_conv(client)
    r = await admin_client.post(
        f"{ADMIN}/conversations/{conv['id']}/messages", json={"content": "بفرمایید"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["sender_role"] == "admin"
    r = await client.get(f"{CHAT}/conversations/{conv['id']}/messages")
    assert [m["sender_role"] for m in r.json()] == ["admin"]


async def test_status_lifecycle_and_customer_reopen(client, admin_client):
    await _login(client)
    conv = await _open_conv(client)
    r = await admin_client.post(
        f"{ADMIN}/conversations/{conv['id']}/status", json={"status": "resolved"}
    )
    assert r.status_code == 200

    # a resolved thread is no longer "the live thread" — but writing into it
    # reopens it rather than silently forking a parallel one
    r = await client.post(
        f"{CHAT}/conversations/{conv['id']}/messages", json={"content": "باز کن"}
    )
    assert r.status_code == 200
    r = await client.get(f"{CHAT}/conversations")
    assert r.json()[0]["status"] == "open"


async def test_chat_requires_auth(client):
    # no admin_client fixture here — its require_admin override is app-global
    r = await client.post(f"{CHAT}/conversations", json={})
    assert r.status_code == 401
    r = await client.get(f"{ADMIN}/conversations")
    assert r.status_code == 401


# ---- WS units: ticket, sub authorization, socket registry ----


async def test_ws_ticket_roundtrip_and_tamper():
    t = issue_ws_ticket("customer", "abc")
    assert read_ws_ticket(t) == ("customer", "abc")
    assert read_ws_ticket(t + "x") is None
    assert read_ws_ticket(None) is None


async def test_ws_sub_authorization(client):
    await _login(client, phone="09121111111")
    conv = await _open_conv(client)
    me = (await client.get(f"{ACC}/me")).json()

    ok = await _authorized_conv(conv["id"], "customer", me["id"])
    assert ok is not None and str(ok.id) == conv["id"]
    # another customer: denied; admin: allowed; garbage id: denied
    assert await _authorized_conv(conv["id"], "customer", str(uuid.uuid4())) is None
    assert await _authorized_conv(conv["id"], "admin", "admin") is not None
    assert await _authorized_conv("not-a-uuid", "admin", "admin") is None


class _FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        self.sent.append(data)


async def test_manager_cap_join_dispatch():
    m = ConnectionManager()
    socks = [_FakeWS() for _ in range(6)]
    grants = [m.connect(ws, "customer", "u1") for ws in socks]
    assert grants == [True] * 5 + [False]  # per-user cap

    conv_id = uuid.uuid4()
    m.join(socks[0], conv_id)
    m.join(socks[1], conv_id)
    await m.dispatch(f"chat:conv:{conv_id}", {"type": "message"})
    assert socks[0].sent and socks[1].sent and not socks[2].sent

    m.disconnect(socks[0], "customer", "u1")
    await m.dispatch(f"chat:conv:{conv_id}", {"type": "message"})
    assert len(socks[0].sent) == 1  # gone after disconnect
    assert len(socks[1].sent) == 2

    # admin sockets get the inbox feed channel
    admin_ws = _FakeWS()
    m.connect(admin_ws, "admin", "boss")
    await m.dispatch("chat:admin", {"type": "conversation"})
    assert admin_ws.sent
