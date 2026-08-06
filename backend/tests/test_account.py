import uuid

import pytest

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
async def test_my_orders_lists_orders_for_phone(client, admin_client, order_payload):
    p = await _make_product(admin_client, price=100)
    await client.post(
        "/api/v1/orders",
        json=order_payload(items=[{"product_id": p["id"], "quantity": 2}]),
    )
    await _login(client, "09121234567")  # same phone as order_payload default
    r = await client.get(f"{ACC}/me/orders")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 1
    assert orders[0]["total"] == "200"
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
            "title": "منزل", "province": "Tehran",
            "line": "خیابان الف", "is_default": True,
        },
    )
    assert a.status_code == 201
    a_id = a.json()["id"]

    # A second default demotes the first.
    b = await client.post(
        f"{ACC}/me/addresses",
        json={
            "title": "محل کار", "province": "Tehran",
            "line": "خیابان ب", "is_default": True,
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
