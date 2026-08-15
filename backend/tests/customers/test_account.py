import uuid
from decimal import Decimal

import pytest

from app.domains.customers import Customer

pytestmark = pytest.mark.asyncio(loop_scope="session")

ACC = "/api/v1/account"


async def _login(client, phone="09121234567"):
    """OTP request → verify (dev_code is returned outside prod). Cookie persists
    on the client for subsequent authed calls."""
    r = await client.post(f"{ACC}/otp/request", json={"phone": phone})
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    assert code and len(code) == 6
    r = await client.post(f"{ACC}/otp/verify", json={"phone": phone, "code": code})
    assert r.status_code == 200, r.text
    return r.json()


async def _make_product(admin_client, **over):
    body = {"name": "Ring", "sku": f"R-{uuid.uuid4().hex[:8]}", **over}
    r = await admin_client.post("/api/v1/admin/products", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---- Auth ----
async def test_otp_login_creates_customer_and_session(client):
    me_before = await client.get(f"{ACC}/me")
    assert me_before.status_code == 401  # no session yet

    cust = await _login(client)
    assert cust["phone"] == "09121234567"
    assert cust["full_name"] is None

    me = await client.get(f"{ACC}/me")
    assert me.status_code == 200
    assert me.json()["id"] == cust["id"]


async def test_otp_verify_wrong_code_401s_session(client):
    await client.post(f"{ACC}/otp/request", json={"phone": "09121234567"})
    r = await client.post(
        f"{ACC}/otp/verify", json={"phone": "09121234567", "code": "000000"}
    )
    assert r.status_code == 400
    assert (await client.get(f"{ACC}/me")).status_code == 401


async def test_login_is_idempotent_per_phone(client):
    a = await _login(client, "09120000001")
    b = await _login(client, "09120000001")
    assert a["id"] == b["id"]  # same phone => same customer row


async def test_logout_clears_session(client):
    await _login(client)
    await client.post(f"{ACC}/logout")
    assert (await client.get(f"{ACC}/me")).status_code == 401


async def test_update_profile(client):
    await _login(client)
    r = await client.patch(f"{ACC}/me", json={"full_name": "علی رضایی"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "علی رضایی"


# ---- Orders (linked by phone) ----
async def test_my_orders_lists_orders_for_phone(
    approved_client, admin_client, order_payload
):
    p = await _make_product(admin_client, weight_grams=100)
    # approved_client is a logged-in, approved customer; the order phone is bound
    # from its session, so /me/orders (linked by phone) sees exactly this order.
    await approved_client.post(
        "/api/v1/orders",
        json=order_payload(items=[{"product_id": p["id"], "quantity": 2}]),
    )
    r = await approved_client.get(f"{ACC}/me/orders")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 1
    assert Decimal(orders[0]["total"]) == 200  # total grams
    assert "internal_note" not in orders[0]  # admin-only field never exposed


async def test_my_orders_requires_auth(client):
    assert (await client.get(f"{ACC}/me/orders")).status_code == 401


# ---- Favorites ----
async def test_favorites_add_list_remove(client, admin_client):
    p = await _make_product(admin_client)
    await _login(client)

    assert (await client.put(f"{ACC}/me/favorites/{p['id']}")).status_code == 204
    # idempotent — second add is still 204, no dupe
    assert (await client.put(f"{ACC}/me/favorites/{p['id']}")).status_code == 204

    fav = await client.get(f"{ACC}/me/favorites")
    assert [x["id"] for x in fav.json()] == [p["id"]]

    assert (await client.delete(f"{ACC}/me/favorites/{p['id']}")).status_code == 204
    assert (await client.get(f"{ACC}/me/favorites")).json() == []


async def test_favorite_unknown_product_404(client):
    await _login(client)
    r = await client.put(f"{ACC}/me/favorites/{uuid.uuid4()}")
    assert r.status_code == 404


# ---- Addresses ----
async def test_address_crud_and_single_default(client):
    await _login(client)
    a = await client.post(
        f"{ACC}/me/addresses",
        json={
            "title": "منزل",
            "province": "Tehran",
            "line": "خیابان الف",
            "is_default": True,
        },
    )
    assert a.status_code == 201
    a_id = a.json()["id"]

    # A second default demotes the first.
    b = await client.post(
        f"{ACC}/me/addresses",
        json={
            "title": "محل کار",
            "province": "Tehran",
            "line": "خیابان ب",
            "is_default": True,
        },
    )
    assert b.status_code == 201
    rows = (await client.get(f"{ACC}/me/addresses")).json()
    lst = {x["id"]: x["is_default"] for x in rows}
    assert lst[a_id] is False and lst[b.json()["id"]] is True

    # Patch + delete.
    up = await client.patch(f"{ACC}/me/addresses/{a_id}", json={"title": "خانه"})
    assert up.status_code == 200 and up.json()["title"] == "خانه"
    assert (await client.delete(f"{ACC}/me/addresses/{a_id}")).status_code == 204


async def test_address_bad_province_422(client):
    await _login(client)
    r = await client.post(
        f"{ACC}/me/addresses",
        json={"title": "x", "province": "Atlantis", "line": "yyy"},
    )
    assert r.status_code == 422


async def test_addresses_require_auth(client):
    assert (await client.get(f"{ACC}/me/addresses")).status_code == 401


async def test_new_customer_is_unverified_with_no_docs(client):
    cust = await _login(client, "09120000010")
    assert cust["verification_status"] == "unverified"
    assert cust["verification_documents"] == []
    assert cust["rejection_reason"] is None
    assert cust["store_name"] is None


async def test_upload_document_sets_pending(client):
    await _login(client, "09120000011")
    r = await client.post(
        f"{ACC}/me/documents",
        files={"file": ("license.png", b"\x89PNG\r\n\x1a\n" + b"fake", "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verification_status"] == "pending"
    assert len(body["verification_documents"]) == 1
    assert body["verification_documents"][0]["url"].startswith("/media/")


async def test_reject_unsupported_document_type(client):
    await _login(client, "09120000012")
    r = await client.post(
        f"{ACC}/me/documents",
        files={"file": ("x.txt", b"nope", "text/plain")},
    )
    assert r.status_code == 415


async def test_delete_document_while_pending(client):
    await _login(client, "09120000013")
    await client.post(
        f"{ACC}/me/documents",
        files={"file": ("l.png", b"\x89PNG\r\n\x1a\n" + b"fake", "image/png")},
    )
    r = await client.delete(f"{ACC}/me/documents/0")
    assert r.status_code == 200
    assert r.json()["verification_documents"] == []


# ---- extra auth / edge cases ----
async def test_verify_without_prior_request_is_400(client):
    # No OTP ever issued for this phone => no code row => invalid.
    r = await client.post(
        f"{ACC}/otp/verify", json={"phone": "09121234567", "code": "123456"}
    )
    assert r.status_code == 400


async def test_me_after_customer_row_deleted_is_401(client, _sessionmaker):
    cust = await _login(client)
    async with _sessionmaker() as db:
        row = await db.get(Customer, uuid.UUID(cust["id"]))
        await db.delete(row)
        await db.commit()
    # Cookie is still valid-signed, but the customer no longer exists.
    assert (await client.get(f"{ACC}/me")).status_code == 401


async def _add_address(client, **over):
    body = {"title": "منزل", "province": "Tehran", "line": "خیابان الف"}
    body.update(over)
    r = await client.post(f"{ACC}/me/addresses", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_patch_address_set_default_demotes_previous(client):
    await _login(client)
    a = await _add_address(client, title="A", is_default=True)
    b = await _add_address(client, title="B", is_default=False)

    up = await client.patch(
        f"{ACC}/me/addresses/{b['id']}",
        json={"is_default": True, "province": "Tehran"},  # valid province exercises validator
    )
    assert up.status_code == 200 and up.json()["is_default"] is True
    assert up.json()["province"] == "Tehran"

    rows = {x["id"]: x["is_default"] for x in (await client.get(f"{ACC}/me/addresses")).json()}
    assert rows[a["id"]] is False and rows[b["id"]] is True  # single default enforced


async def test_patch_address_bad_province_422(client):
    await _login(client)
    a = await _add_address(client)
    r = await client.patch(
        f"{ACC}/me/addresses/{a['id']}", json={"province": "Atlantis"}
    )
    assert r.status_code == 422


async def test_patch_unknown_address_404(client):
    await _login(client)
    r = await client.patch(f"{ACC}/me/addresses/{uuid.uuid4()}", json={"title": "x"})
    assert r.status_code == 404


async def test_delete_unknown_address_404(client):
    await _login(client)
    r = await client.delete(f"{ACC}/me/addresses/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_otp_test_phone_reveals_code_in_prod(client, monkeypatch):
    """An allowlisted test phone gets dev_code back (and skips the real SMS) even
    when cookie_secure=True (production); other phones don't."""
    import app.domains.customers.actions.request_otp_action as account
    from app.core.config import settings

    sent: list[str] = []

    async def _spy_sms(phone, msg):
        sent.append(phone)

    monkeypatch.setattr(account, "send_sms", _spy_sms)
    monkeypatch.setattr(settings, "cookie_secure", True)  # simulate prod
    monkeypatch.setattr(settings, "otp_test_phones", "09028068820")

    # Normal phone in prod: no dev_code, real SMS attempted.
    r = await client.post(f"{ACC}/otp/request", json={"phone": "09121234567"})
    assert r.status_code == 200 and r.json()["dev_code"] is None
    assert "09121234567" in sent

    # Test phone in prod: dev_code returned, SMS skipped.
    r = await client.post(f"{ACC}/otp/request", json={"phone": "09028068820"})
    assert r.status_code == 200
    assert r.json()["dev_code"] and len(r.json()["dev_code"]) == 6
    assert "09028068820" not in sent


async def test_document_with_spoofed_type_rejected(client):
    """A .png claim with non-PNG bytes must be refused (magic-byte check)."""
    await _login(client, "09120000019")
    r = await client.post(
        f"{ACC}/me/documents",
        files={"file": ("evil.png", b"MZ\x90\x00 not a png", "image/png")},
    )
    assert r.status_code == 415
