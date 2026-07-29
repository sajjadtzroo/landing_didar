import uuid

import pytest

from app.api.limiter import limiter

pytestmark = pytest.mark.asyncio(loop_scope="session")

ORDERS = "/api/v1/orders"


async def _make_product(admin_client, **over):
    body = {"name": "Ring", "sku": f"R-{uuid.uuid4().hex[:8]}", **over}
    r = await admin_client.post("/api/v1/admin/products", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---- GET /products ----
async def test_list_products_empty(client):
    r = await client.get("/api/v1/products")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_products_hides_inactive_and_sorts(client, admin_client):
    await _make_product(admin_client, name="B", sort_order=2)
    await _make_product(admin_client, name="A", sort_order=1)
    await _make_product(admin_client, name="Hidden", is_active=False)

    r = await client.get("/api/v1/products")
    names = [p["name"] for p in r.json()]
    assert names == ["A", "B"]  # inactive excluded, sorted by sort_order


# ---- GET /faqs ----
async def test_list_faqs_hides_inactive(client, admin_client):
    await admin_client.post(
        "/api/v1/admin/faqs", json={"question": "Q1", "answer": "A1"}
    )
    await admin_client.post(
        "/api/v1/admin/faqs",
        json={"question": "Q2", "answer": "A2", "is_active": False},
    )
    r = await client.get("/api/v1/faqs")
    assert [f["question"] for f in r.json()] == ["Q1"]


# ---- POST /orders ----
async def test_create_order_custom_item(client, order_payload):
    r = await client.post(ORDERS, json=order_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reference"].startswith("DG-")
    assert body["total"] == "0"  # no product_id => "custom item", price unknown


async def test_create_order_totals_from_product(client, admin_client, order_payload):
    p = await _make_product(admin_client, price=100)
    r = await client.post(
        ORDERS,
        json=order_payload(items=[{"product_id": p["id"], "quantity": 3}]),
    )
    assert r.status_code == 201
    assert r.json()["total"] == "300"  # server-trusted price * qty


async def test_honeypot_returns_fake_and_persists_nothing(
    client, admin_client, order_payload
):
    r = await client.post(ORDERS, json=order_payload(website="spam"))
    assert r.status_code == 201
    assert r.json() == {"reference": "DG-000000", "total": "0"}
    # nothing stored
    listed = await admin_client.get("/api/v1/admin/orders")
    assert listed.json()["total"] == 0


async def test_idempotency_key_dedupes(client, admin_client, order_payload):
    hdr = {"Idempotency-Key": str(uuid.uuid4())}
    r1 = await client.post(ORDERS, json=order_payload(), headers=hdr)
    r2 = await client.post(ORDERS, json=order_payload(), headers=hdr)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["reference"] == r2.json()["reference"]
    listed = await admin_client.get("/api/v1/admin/orders")
    assert listed.json()["total"] == 1  # only one row


@pytest.mark.parametrize(
    "override",
    [
        {"phone": "0912"},            # bad phone
        {"province": "Atlantis"},     # not an Iran province
        {"items": []},               # needs >= 1 item
        {"full_name": "Al"},         # too short
    ],
)
async def test_create_order_validation(client, order_payload, override):
    r = await client.post(ORDERS, json=order_payload(**override))
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body and "field" in body  # consistent error envelope


async def test_rate_limit_after_five(client, order_payload):
    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001 — older slowapi has no reset(); storage is fresh
        pass
    codes = []
    for _ in range(6):
        codes.append((await client.post(ORDERS, json=order_payload())).status_code)
    limiter.enabled = False
    assert codes.count(201) == 5
    assert codes[-1] == 429
