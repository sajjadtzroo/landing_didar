import hashlib
import secrets
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus, OrderStatusLog
from app.models.product import Product
from app.schemas.order import OrderCreate

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

    total = Decimal(0)
    items: list[OrderItem] = []
    for it in payload.items:
        p = products.get(it.product_id) if it.product_id else None
        name = p.name if p else "Custom item"
        unit_price = p.price if p else None
        if unit_price is not None:
            total += Decimal(unit_price) * it.quantity
        items.append(
            OrderItem(
                product_id=p.id if p else None,
                product_name=name,
                unit_price=unit_price,
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
    await db.commit()
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
