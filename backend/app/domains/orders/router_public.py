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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip
from app.api.limiter import limiter
from app.core.config import settings
from app.core.db import get_db
from app.domains.customers import (
    Customer,
    CustomerVerificationStatus,
    require_customer,
)
from app.domains.orders import service as order_service
from app.domains.orders.models import Order
from app.domains.orders.notifications import get_adapter
from app.domains.orders.schemas import OrderCreate, OrderCreatedOut, OrderTrackOut

router = APIRouter()


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
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    # Only an admin-approved customer may order; bind the phone from the
    # verified session so a client-supplied phone can never be trusted.
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if customer.verification_status != CustomerVerificationStatus.approved:
        raise HTTPException(status_code=403, detail="حساب شما هنوز تأیید نشده است")
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
    # Notify AFTER commit, in the background — never rolls back the order.
    background.add_task(_notify, order.id, settings.admin_order_base_url)
    return OrderCreatedOut(reference=order.reference, total=order.total)
