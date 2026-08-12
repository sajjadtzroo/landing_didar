"""Public order routes (checkout + account-less tracking).

Moved verbatim from app/api/v1/public.py during the domain migration;
registered with tags=["public"] so OpenAPI is unchanged."""

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
)
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.core.security import get_client_ip
from app.domains.catalog import Product, ProductOut
from app.domains.customers import Customer, optional_customer
from app.domains.orders import service as order_service
from app.domains.orders.models import Order, OrderItem, OrderStatus
from app.domains.orders.notifications import get_adapter
from app.domains.orders.schemas import OrderCreate, OrderCreatedOut, OrderTrackOut

router = APIRouter()

_BEST_SELLERS_TTL = 300.0  # sales rankings move slowly; save the join


@router.get("/products/best-sellers", response_model=list[ProductOut])
async def best_sellers(response: Response, db: AsyncSession = Depends(get_db)):
    """Top products by units actually sold (order_items, non-cancelled orders).
    Lives in the orders domain because sales data does; registered BEFORE the
    catalog router so /products/{slug} doesn't swallow the path."""
    response.headers["Cache-Control"] = "public, max-age=300"
    cached = await cache_get("cache:best-sellers")
    if cached is not None:
        return cached
    rows = (
        await db.execute(
            select(Product)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Product.is_active,
                Product.product_status != "not_for_sale",
                Order.status != OrderStatus.cancelled,
            )
            .group_by(Product.id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(8)
        )
    ).scalars().all()
    items = [ProductOut.model_validate(p) for p in rows]
    await cache_set("cache:best-sellers", items, _BEST_SELLERS_TTL)
    return items


@router.get("/orders/track", response_model=OrderTrackOut)
async def track_order(
    reference: str,
    phone: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Account-less order tracking. Both reference AND the ordering phone must
    match — an unknown reference and a wrong phone return the SAME 404 so a
    reference can't be enumerated without the phone. Never cached (status changes).
    """
    response.headers["Cache-Control"] = "no-store"
    order = (
        await db.execute(select(Order).where(Order.reference == reference.strip()))
    ).scalar_one_or_none()
    if order is None or order.phone != phone.strip():
        raise HTTPException(404, detail="Order not found")
    return order


async def _notify(order_id, admin_url: str) -> None:
    """Background task: re-loads the order in a fresh session (the request session
    is closed by now) and notifies. Failure logs + retries once, never blocks."""
    from app.core.db import SessionLocal
    from app.domains.orders.models import Order

    adapter = get_adapter()
    async with SessionLocal() as db:
        order = await db.get(Order, order_id)
        if order is None:
            return
        for attempt in (1, 2):
            try:
                await adapter.send_new_order(order, admin_url)
                return
            except Exception:  # noqa: BLE001
                logger.exception("order notification failed (attempt {})", attempt)


@router.post("/orders", response_model=OrderCreatedOut, status_code=201)
@limiter.limit("5/hour")
async def create_order(
    request: Request,
    payload: OrderCreate,
    background: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    customer_id: uuid.UUID | None = Depends(optional_customer),
    db: AsyncSession = Depends(get_db),
):
    # Guest checkout: no login required. A logged-in session still binds the
    # phone from the verified customer (client value can't override it); guests
    # supply their own phone, and a later OTP login with that phone claims the
    # order — /me/orders links orders to customers by phone.
    if customer_id is not None:
        customer = await db.get(Customer, customer_id)
        if customer is not None:
            payload.phone = customer.phone

    # Honeypot: bots fill hidden fields; pretend success without persisting.
    if payload.website:
        return OrderCreatedOut(reference="DG-000000", total=0)

    # Idempotency: a repeated key returns the original order (double-tap safe).
    if idempotency_key:
        existing = await order_service.get_order_by_key(db, idempotency_key)
        if existing:
            return OrderCreatedOut(reference=existing.reference, total=existing.total)

    order = await order_service.create_order(
        db, payload, idempotency_key, get_client_ip(request)
    )
    # Auto-register the guest as a customer (identity = phone) so they show up
    # in the admin customers panel immediately; a later OTP login with the same
    # phone lands on this account. Separate commit — never rolls back the order.
    if customer_id is None:
        exists = (
            await db.execute(select(Customer).where(Customer.phone == payload.phone))
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                Customer(
                    phone=payload.phone,
                    full_name=payload.full_name,
                    store_name=payload.store_name,
                )
            )
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()  # concurrent order with same phone won the race
    # Notify AFTER commit, in the background — never rolls back the order.
    background.add_task(_notify, order.id, settings.admin_order_base_url)
    return OrderCreatedOut(reference=order.reference, total=order.total)
