"""Service-level tests for order creation logic that the HTTP tests don't reach:
the idempotency-race recovery, custom (product-less) items, change_status, and the
small helpers. Exercised directly against the test session."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domains.orders import Order, OrderCreate, OrderStatus
from app.domains.orders import service as svc
from app.domains.orders.actions import create_order_action as _create_mod

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _payload(**over):
    base = dict(
        full_name="Ali Rezaei",
        phone="09121234567",
        store_name="Rezaei Jewelry",
        province="Tehran",
        items=[{"quantity": 2}],  # no product_id => custom item
    )
    base.update(over)
    return OrderCreate(**base)


# ---- pure helpers (async only to satisfy this module's asyncio pytestmark) ----
async def test_hash_ip_none_returns_none():
    assert svc.hash_ip(None) is None


async def test_hash_ip_hashes_deterministically():
    h = svc.hash_ip("1.2.3.4")
    assert h == svc.hash_ip("1.2.3.4") and len(h) == 64  # sha256 hex
    assert h != svc.hash_ip("1.2.3.5")


async def test_get_order_by_key_empty_key_returns_none(_sessionmaker):
    async with _sessionmaker() as db:
        assert await svc.get_order_by_key(db, "") is None


# ---- create_order ----
async def test_create_order_custom_item_has_no_weight(_sessionmaker):
    async with _sessionmaker() as db:
        order = await svc.create_order(db, _payload(), None, "1.2.3.4")
    assert order.reference.startswith("DG-")
    assert order.total == 0  # unknown weight contributes nothing
    assert order.items[0].product_name == "Custom item"
    assert order.items[0].unit_weight_grams is None
    assert order.ip_hash is not None  # ip was hashed


async def test_change_status_noop_then_transition(_sessionmaker):
    async with _sessionmaker() as db:
        order = await svc.create_order(db, _payload(), None, None)
        logs_before = len(order.status_log)

        await svc.change_status(db, order, order.status)  # same status: no-op
        assert len(order.status_log) == logs_before

        await svc.change_status(db, order, OrderStatus.confirmed)
        assert order.status == OrderStatus.confirmed
        assert len(order.status_log) == logs_before + 1
        assert order.status_log[-1].to_status == OrderStatus.confirmed


async def test_idempotency_race_returns_the_winning_row(_sessionmaker):
    key = "race-key-123"
    # Two independent sessions both try to create with the same key. The first
    # wins; the second hits the unique constraint, rolls back, and returns the
    # existing order instead of raising.
    async with _sessionmaker() as db1:
        first = await svc.create_order(db1, _payload(), key, None)
    async with _sessionmaker() as db2:
        second = await svc.create_order(db2, _payload(), key, None)

    assert second.reference == first.reference

    async with _sessionmaker() as db3:
        rows = (
            await db3.execute(select(Order).where(Order.idempotency_key == key))
        ).scalars().all()
    assert len(rows) == 1  # exactly one row persisted


async def test_unexpected_integrity_error_is_reraised(_sessionmaker, monkeypatch):
    # Force a reference collision (a NON-idempotency constraint) with no key —
    # there's nothing to recover to, so the IntegrityError must propagate.
    monkeypatch.setattr(_create_mod, "_reference", lambda: "DG-DUPES")
    async with _sessionmaker() as db1:
        await svc.create_order(db1, _payload(), None, None)
    async with _sessionmaker() as db2:
        with pytest.raises(IntegrityError):
            await svc.create_order(db2, _payload(), None, None)
