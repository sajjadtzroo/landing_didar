"""Feature tests for the admin dashboard read model (DashboardQuery.stats).

Orders are seeded through the real public/admin routes; time-window tests
backdate rows directly (created_at is server-stamped, not settable via API).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.domains.orders import OrderStatus

pytestmark = pytest.mark.asyncio(loop_scope="session")

STATS = "/api/v1/admin/stats"
ORDERS = "/api/v1/orders"
ADMIN_ORDERS = "/api/v1/admin/orders"


async def _product(admin_client, name="Chain", weight=5):
    r = await admin_client.post(
        "/api/v1/admin/products",
        json={
            "name": name,
            "sku": f"SKU-{uuid.uuid4().hex[:8]}",
            "weight_grams": weight,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _order(approved_client, order_payload, **over):
    r = await approved_client.post(ORDERS, json=order_payload(**over))
    assert r.status_code == 201, r.text
    return r.json()["reference"]


async def _backdate(_sessionmaker, reference: str, days: int) -> None:
    async with _sessionmaker() as db:
        await db.execute(
            text(
                "UPDATE orders SET created_at = now() - make_interval(days => :d) "
                "WHERE reference = :r"
            ),
            {"d": days, "r": reference},
        )
        await db.commit()


async def _set_status(admin_client, reference: str, status: str) -> None:
    listing = (await admin_client.get(ADMIN_ORDERS, params={"q": reference})).json()
    oid = listing["items"][0]["id"]
    r = await admin_client.patch(f"{ADMIN_ORDERS}/{oid}", json={"status": status})
    assert r.status_code == 200, r.text


async def _stats(admin_client) -> dict:
    r = await admin_client.get(STATS)
    assert r.status_code == 200
    return r.json()


async def test_counts_since_windows(
    approved_client, admin_client, order_payload, _sessionmaker
):
    today = await _order(approved_client, order_payload)  # noqa: F841 — stays "today"
    this_week = await _order(approved_client, order_payload)
    this_month = await _order(approved_client, order_payload)
    await _backdate(_sessionmaker, this_week, 3)
    await _backdate(_sessionmaker, this_month, 20)

    body = await _stats(admin_client)
    assert body["orders_today"] == 1
    assert body["orders_week"] == 2
    assert body["orders_month"] == 3
    assert body["total_orders"] == 3


async def test_orders_by_day_zero_filled_shape(admin_client):
    series = (await _stats(admin_client))["orders_by_day"]
    assert len(series) == 14
    assert all(p["count"] == 0 for p in series)
    dates = [p["date"] for p in series]
    assert dates == sorted(dates)  # oldest → newest, continuous for the chart
    assert dates[-1] == datetime.now(UTC).date().isoformat()


async def test_orders_by_day_buckets_and_window(
    approved_client, admin_client, order_payload, _sessionmaker
):
    await _order(approved_client, order_payload)
    await _order(approved_client, order_payload)
    old = await _order(approved_client, order_payload)
    ancient = await _order(approved_client, order_payload)
    await _backdate(_sessionmaker, old, 5)
    await _backdate(_sessionmaker, ancient, 20)

    series = (await _stats(admin_client))["orders_by_day"]
    by_date = {p["date"]: p["count"] for p in series}
    now = datetime.now(UTC)
    assert by_date[now.date().isoformat()] == 2
    assert by_date[(now - timedelta(days=5)).date().isoformat()] == 1
    # the 20-day-old order falls outside the 14-day window entirely
    assert sum(by_date.values()) == 3


async def test_by_status_covers_all_statuses_zero_filled(
    approved_client, admin_client, order_payload
):
    await _order(approved_client, order_payload)
    confirmed = await _order(approved_client, order_payload)
    await _set_status(admin_client, confirmed, "confirmed")

    body = await _stats(admin_client)
    by_status = {e["status"]: e["count"] for e in body["by_status"]}
    assert set(by_status) == {s.value for s in OrderStatus}  # zero-filled, all 7
    assert by_status["new"] == 1
    assert by_status["confirmed"] == 1
    assert by_status["cancelled"] == 0


async def test_conversion_rate_math(approved_client, admin_client, order_payload):
    refs = [await _order(approved_client, order_payload) for _ in range(4)]
    await _set_status(admin_client, refs[0], "confirmed")
    await _set_status(admin_client, refs[1], "shipped")
    await _set_status(admin_client, refs[2], "cancelled")  # not converted
    # refs[3] stays "new" — not converted

    body = await _stats(admin_client)
    assert body["conversion_rate"] == round(2 / 4, 3) == 0.5


async def test_top_products_aggregates_across_orders(
    approved_client, admin_client, order_payload
):
    a = await _product(admin_client, name="Chain A")
    b = await _product(admin_client, name="Ring B")
    await _order(
        approved_client, order_payload, items=[{"product_id": a["id"], "quantity": 2}]
    )
    await _order(
        approved_client,
        order_payload,
        items=[
            {"product_id": a["id"], "quantity": 3},
            {"product_id": b["id"], "quantity": 2},
        ],
    )

    top = (await _stats(admin_client))["top_products"]
    assert top == [
        {"name": "Chain A", "quantity": 5},  # summed across both orders
        {"name": "Ring B", "quantity": 2},
    ]


async def test_by_province_ordered_by_count_desc(
    approved_client, admin_client, order_payload
):
    await _order(approved_client, order_payload, province="Tehran")
    await _order(approved_client, order_payload, province="Tehran")
    await _order(approved_client, order_payload, province="Isfahan")

    by_province = (await _stats(admin_client))["by_province"]
    assert by_province[0] == {"province": "Tehran", "count": 2}
    assert {"province": "Isfahan", "count": 1} in by_province


async def test_total_value_sums_grams(approved_client, admin_client, order_payload):
    p = await _product(admin_client, weight=5)
    await _order(
        approved_client, order_payload, items=[{"product_id": p["id"], "quantity": 2}]
    )
    await _order(
        approved_client, order_payload, items=[{"product_id": p["id"], "quantity": 1}]
    )

    # total is order size in grams: 5 g × (2 + 1)
    assert (await _stats(admin_client))["total_value"] == 15.0


async def test_unread_reflects_read_flag(approved_client, admin_client, order_payload):
    ref = await _order(approved_client, order_payload)
    await _order(approved_client, order_payload)
    assert (await _stats(admin_client))["unread"] == 2

    listing = (await admin_client.get(ADMIN_ORDERS, params={"q": ref})).json()
    await admin_client.patch(
        f"{ADMIN_ORDERS}/{listing['items'][0]['id']}", json={"is_read": True}
    )
    assert (await _stats(admin_client))["unread"] == 1
