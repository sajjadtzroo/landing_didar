import pytest

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
        files={"file": ("l.png", b"x", "image/png")},
    )


async def test_admin_lists_pending_customers(client, admin_client):
    await _submit_docs(client, "09120000021")
    r = await admin_client.get(f"{ADM}?status=pending")
    assert r.status_code == 200
    assert any(c["phone"] == "09120000021" for c in r.json())


async def test_admin_approve_sets_status_and_sms(client, admin_client):
    # caplog does not capture loguru output in this project (loguru bypasses
    # stdlib logging); assert on response JSON only as the brief permits.
    await _submit_docs(client, "09120000022")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    r = await admin_client.patch(
        f"{ADM}/{cid}/verification", json={"status": "approved"}
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "approved"
    assert r.json()["verified_at"] is not None


async def test_admin_reject_stores_reason(client, admin_client):
    await _submit_docs(client, "09120000023")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    r = await admin_client.patch(
        f"{ADM}/{cid}/verification",
        json={"status": "rejected", "reason": "مدرک ناخواناست"},
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "rejected"
    assert r.json()["rejection_reason"] == "مدرک ناخواناست"
