"""Public order routes (checkout + account-less tracking).

Thin HTTP layer: request-level defenses (rate limit, honeypot, idempotency
pre-check) + one Query/Action call each; registered with tags=["public"] so
OpenAPI is unchanged."""

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

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import get_client_ip
from app.domains.catalog import ProductOut
from app.domains.customers import optional_customer
from app.domains.orders.actions import CreateOrderAction
from app.domains.orders.queries import OrderQuery
from app.domains.orders.schemas import OrderCreate, OrderCreatedOut, OrderTrackOut
from app.domains.orders.services.notifications import get_adapter

router = APIRouter()

_BEST_SELLERS_TTL = 300.0  # sales rankings move slowly; save the join


@router.get("/products/best-sellers", response_model=list[ProductOut])
async def best_sellers(response: Response, orders: OrderQuery = Depends()):
    """Top products by units actually sold (order_items, non-cancelled orders).
    Lives in the orders domain because sales data does; registered BEFORE the
    catalog router so /products/{slug} doesn't swallow the path."""
    response.headers["Cache-Control"] = "public, max-age=300"
    cached = await cache_get("cache:best-sellers")
    if cached is not None:
        return cached
    items = [
        ProductOut.model_validate(p) for p in await orders.best_seller_products()
    ]
    await cache_set("cache:best-sellers", items, _BEST_SELLERS_TTL)
    return items


@router.get("/orders/track", response_model=OrderTrackOut)
async def track_order(
    reference: str,
    phone: str,
    response: Response,
    orders: OrderQuery = Depends(),
):
    """Account-less order tracking. Both reference AND the ordering phone must
    match — an unknown reference and a wrong phone return the SAME 404 so a
    reference can't be enumerated without the phone. Never cached (status changes).
    """
    response.headers["Cache-Control"] = "no-store"
    order = await orders.by_reference(reference)
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
    orders: OrderQuery = Depends(),
    create: CreateOrderAction = Depends(),
):
    # Honeypot: bots fill hidden fields; pretend success without persisting.
    if payload.website:
        return OrderCreatedOut(reference="DG-000000", total=0)

    # Idempotency: a repeated key returns the original order (double-tap safe)
    # without re-notifying sales.
    if idempotency_key:
        existing = await orders.by_idempotency_key(idempotency_key)
        if existing:
            return OrderCreatedOut(reference=existing.reference, total=existing.total)

    order = await create.checkout(
        payload,
        idempotency_key=idempotency_key,
        ip=get_client_ip(request),
        customer_id=customer_id,
    )
    # Notify AFTER commit, in the background — never rolls back the order.
    background.add_task(_notify, order.id, settings.admin_order_base_url)
    return OrderCreatedOut(reference=order.reference, total=order.total)
