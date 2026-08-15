"""DEPRECATED compat shim — the write side lives in orders.actions now.

Kept only for the agents domain + legacy tests; delete once those call
CreateOrderAction / OrderAction directly (Faz 1c of the CQRS-light pass)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.orders.actions import CreateOrderAction, OrderAction
from app.domains.orders.models import Order, OrderStatus
from app.domains.orders.queries import OrderQuery
from app.domains.orders.schemas import OrderCreate
from app.shared.validation import hash_ip  # noqa: F401  — re-export


async def get_order_by_key(db: AsyncSession, key: str) -> Order | None:
    return await OrderQuery(db).by_idempotency_key(key)


async def create_order(
    db: AsyncSession,
    payload: OrderCreate,
    idempotency_key: str | None,
    ip: str | None,
) -> Order:
    return await CreateOrderAction(db).execute(
        payload, idempotency_key=idempotency_key, ip=ip
    )


async def change_status(
    db: AsyncSession, order: Order, to_status: OrderStatus
) -> None:
    await OrderAction(db).change_status(order, to_status)
