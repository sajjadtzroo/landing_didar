import pytest

import app.domains.customers.router_admin as admin_mod

pytestmark = pytest.mark.asyncio(loop_scope="session")

ACC = "/api/v1/account"
ADM = "/api/v1/admin/customers"


async def _login(client, phone):
    r = await client.post(f"{ACC}/otp/request", json={"phone": phone})
    code = r.json()["dev_code"]
    await client.post(f"{ACC}/otp/verify", json={"phone": phone, "code": code})


async def _submit_docs(client, phone):
    await _login(client, phone)
    await client.post(
        f"{ACC}/me/documents",
        files={"file": ("l.png", b"\x89PNG\r\n\x1a\n" + b"fake", "image/png")},
    )


async def test_admin_lists_pending_customers(client, admin_client):
    await _submit_docs(client, "09120000021")
    r = await admin_client.get(f"{ADM}?status=pending")
    assert r.status_code == 200
    assert any(c["phone"] == "09120000021" for c in r.json())


async def test_admin_approve_sets_status_and_sms(client, admin_client, monkeypatch):
    calls = []

    async def _spy(phone, message):
        calls.append((phone, message))

    monkeypatch.setattr(admin_mod, "send_sms", _spy)

    await _submit_docs(client, "09120000022")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    r = await admin_client.patch(
        f"{ADM}/{cid}/verification", json={"status": "approved"}
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "approved"
    assert r.json()["verified_at"] is not None
    assert calls == [("09120000022", "احراز هویت شما با موفقیت انجام شد.")]


async def test_admin_reject_stores_reason(client, admin_client, monkeypatch):
    calls = []

    async def _spy(phone, message):
        calls.append((phone, message))

    monkeypatch.setattr(admin_mod, "send_sms", _spy)

    await _submit_docs(client, "09120000023")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    r = await admin_client.patch(
        f"{ADM}/{cid}/verification",
        json={"status": "rejected", "reason": "مدرک ناخواناست"},
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "rejected"
    assert r.json()["rejection_reason"] == "مدرک ناخواناست"
    assert len(calls) == 1
    assert "مدرک ناخواناست" in calls[0][1]


async def test_approve_noop_skips_sms(client, admin_client, monkeypatch):
    # Patch an already-approved customer again — no SMS should fire.
    calls = []

    async def _spy(phone, message):
        calls.append((phone, message))

    monkeypatch.setattr(admin_mod, "send_sms", _spy)

    await _submit_docs(client, "09120000024")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    # First approval — fires SMS (we don't care, just move past it)
    await admin_client.patch(f"{ADM}/{cid}/verification", json={"status": "approved"})
    calls.clear()
    # Second PATCH with same status — must be a no-op
    r = await admin_client.patch(
        f"{ADM}/{cid}/verification", json={"status": "approved"}
    )
    assert r.status_code == 200
    assert calls == []  # ponytail: guards the early-return branch
