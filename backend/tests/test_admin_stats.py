import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

STATS = "/api/v1/admin/stats"


async def test_requires_auth(client):
    assert (await client.get(STATS)).status_code == 401


async def test_stats_empty(admin_client):
    body = (await admin_client.get(STATS)).json()
    assert body["orders_today"] == 0
    assert body["conversion_rate"] == 0
    assert body["top_products"] == []
    assert body["by_province"] == []


async def test_stats_with_data(approved_client, admin_client, order_payload):
    p = (
        await admin_client.post(
            "/api/v1/admin/products",
            json={"name": "Chain", "sku": f"C-{uuid.uuid4().hex[:8]}", "weight_grams": 5},
        )
    ).json()
    await approved_client.post(
        "/api/v1/orders",
        json=order_payload(items=[{"product_id": p["id"], "quantity": 2}]),
    )

    body = (await admin_client.get(STATS)).json()
    assert body["orders_today"] == 1
    assert {"name": "Chain", "quantity": 2} in body["top_products"]
    assert {"province": "Tehran", "count": 1} in body["by_province"]
    assert body["conversion_rate"] == 0  # order is "new", not confirmed/shipped
