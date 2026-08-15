"""Public /products/best-sellers: ranked by units sold, cancelled excluded."""

import pytest

from app.domains.orders import Order, OrderItem, OrderStatus

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _product(admin_client, name, slug):
    r = await admin_client.post(
        "/api/v1/admin/products",
        json={"name": name, "slug": slug, "sku": f"BS-{slug}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _order_with(sessionmaker, status, items):
    async with sessionmaker() as db:
        order = Order(
            reference=f"DG-{status[:3].upper()}{len(items)}{items[0][1]}",
            full_name="x",
            phone="09120000000",
            store_name="s",
            province="Tehran",
            status=OrderStatus(status),
        )
        db.add(order)
        await db.flush()
        for pid, qty, name in items:
            db.add(
                OrderItem(
                    order_id=order.id, product_id=pid, product_name=name, quantity=qty
                )
            )
        await db.commit()


async def test_ranked_by_units_and_cancelled_excluded(
    client, admin_client, _sessionmaker
):
    a = await _product(admin_client, "کم‌فروش", "bs-low")
    b = await _product(admin_client, "پرفروش", "bs-top")
    c = await _product(admin_client, "لغوشده", "bs-cancelled")

    await _order_with(_sessionmaker, "confirmed", [(a["id"], 2, "کم‌فروش")])
    await _order_with(_sessionmaker, "delivered", [(b["id"], 7, "پرفروش")])
    await _order_with(_sessionmaker, "cancelled", [(c["id"], 99, "لغوشده")])

    r = await client.get("/api/v1/products/best-sellers")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.json()]
    assert slugs == ["bs-top", "bs-low"]  # ranked by qty; cancelled absent


async def test_empty_without_sales(client, admin_client):
    await _product(admin_client, "بی‌سفارش", "bs-none")
    r = await client.get("/api/v1/products/best-sellers")
    assert r.status_code == 200 and r.json() == []
