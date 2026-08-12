import hashlib
import secrets
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog import Product
from app.domains.orders.models import Order, OrderItem, OrderStatus, OrderStatusLog
from app.domains.orders.schemas import OrderCreate

_REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars


def _reference() -> str:
    return "DG-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


async def get_order_by_key(db: AsyncSession, key: str) -> Order | None:
    if not key:
        return None
    res = await db.execute(select(Order).where(Order.idempotency_key == key))
    return res.scalar_one_or_none()


async def create_order(
    db: AsyncSession,
    payload: OrderCreate,
    idempotency_key: str | None,
    ip: str | None,
) -> Order:
    """Create an order, copying product name + price at order time. Line-item
    prices come from the live product (server-trusted), not the client."""
    # Load referenced products in one query; snapshot their name/price.
    product_ids = [it.product_id for it in payload.items if it.product_id]
    products: dict = {}
    if product_ids:
        res = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = {p.id: p for p in res.scalars()}

    # Order size is total GRAMS (wholesale gold — quantified by weight, not Toman).
    total = Decimal(0)
    items: list[OrderItem] = []
    for it in payload.items:
        p = products.get(it.product_id) if it.product_id else None
        name = p.name if p else "Custom item"
        unit_weight = p.weight_grams if p else None
        if unit_weight is not None:
            total += Decimal(unit_weight) * it.quantity
        items.append(
            OrderItem(
                product_id=p.id if p else None,
                product_name=name,
                unit_weight_grams=unit_weight,
                quantity=it.quantity,
            )
        )

    order = Order(
        reference=_reference(),
        full_name=payload.full_name,
        phone=payload.phone,
        store_name=payload.store_name,
        province=payload.province,
        city=payload.city,
        contact_method=payload.contact_method,
        note=payload.note,
        status=OrderStatus.new,
        total=total,
        idempotency_key=idempotency_key or None,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        referrer=payload.referrer,
        ip_hash=hash_ip(ip),
        items=items,
        status_log=[OrderStatusLog(from_status=None, to_status=OrderStatus.new)],
    )
    db.add(order)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent submit with the same Idempotency-Key won the race — the row
        # exists; return the winner instead of 500-ing on the unique violation.
        await db.rollback()
        if idempotency_key:
            existing = await get_order_by_key(db, idempotency_key)
            if existing:
                return existing
        raise
    await db.refresh(order)
    return order


async def change_status(
    db: AsyncSession, order: Order, to_status: OrderStatus
) -> None:
    if order.status == to_status:
        return
    order.status_log.append(
        OrderStatusLog(from_status=order.status, to_status=to_status)
    )
    order.status = to_status
    # Proof of Delivery: stamp the first time the order becomes delivered.
    if to_status == OrderStatus.delivered and order.delivered_at is None:
        order.delivered_at = datetime.now(UTC)
