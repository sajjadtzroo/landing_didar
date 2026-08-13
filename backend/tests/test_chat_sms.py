"""New/reopened conversations alert the admin by SMS (best-effort)."""

import asyncio

import pytest

import app.domains.chat.service as chat_service
from app.core.config import settings

pytestmark = pytest.mark.asyncio(loop_scope="session")

ACC = "/api/v1/account"
CHAT = "/api/v1/account/chat"
ADMIN = "/api/v1/admin/chat"


async def _login(client, phone="09121234567"):
    r = await client.post(f"{ACC}/otp/request", json={"phone": phone})
    r = await client.post(
        f"{ACC}/otp/verify", json={"phone": phone, "code": r.json()["dev_code"]}
    )
    assert r.status_code == 200


async def test_new_and_reopened_conversation_sms_admin(
    client, admin_client, monkeypatch
):
    sent = []

    async def fake_sms(to, message):
        sent.append((to, message))

    monkeypatch.setattr(chat_service, "send_sms", fake_sms)
    monkeypatch.setattr(settings, "sms_admin_phone", "09028068820")

    await _login(client)
    r = await client.post(f"{CHAT}/conversations", json={})
    conv = r.json()
    await asyncio.sleep(0)  # let the fire-and-forget task run
    assert sent and sent[0][0] == "09028068820"

    # get-or-create of the same open thread: no second alert
    await client.post(f"{CHAT}/conversations", json={})
    await asyncio.sleep(0)
    assert len(sent) == 1

    # customer writing into a resolved thread reopens it -> alert again
    await admin_client.post(
        f"{ADMIN}/conversations/{conv['id']}/status", json={"status": "resolved"}
    )
    await client.post(
        f"{CHAT}/conversations/{conv['id']}/messages", json={"content": "هنوز مشکل دارم"}
    )
    await asyncio.sleep(0)
    assert len(sent) == 2


async def test_no_admin_phone_no_sms(client, monkeypatch):
    sent = []

    async def fake_sms(to, message):
        sent.append(to)

    monkeypatch.setattr(chat_service, "send_sms", fake_sms)
    monkeypatch.setattr(settings, "sms_admin_phone", "")

    await _login(client)
    await client.post(f"{CHAT}/conversations", json={})
    await asyncio.sleep(0)
    assert sent == []
