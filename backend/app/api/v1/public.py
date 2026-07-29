from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip
from app.api.limiter import limiter
from app.core.config import settings
from app.core.db import get_db
from app.models.faq import FAQ
from app.models.product import Product
from app.schemas.faq import FAQOut
from app.schemas.order import OrderCreate, OrderCreatedOut
from app.schemas.product import ProductOut
from app.services import orders as order_service
from app.services.notifications import get_adapter

router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
async def list_products(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Product).where(Product.is_active).order_by(Product.sort_order)
    )
    return res.scalars().all()


@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(FAQ).where(FAQ.is_active).order_by(FAQ.sort_order)
    )
    return res.scalars().all()


async def _notify(order_id, admin_url: str) -> None:
    """Background task: re-loads the order in a fresh session (the request session
    is closed by now) and notifies. Failure logs + retries once, never blocks."""
    from app.core.db import SessionLocal
    from app.models.order import Order

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
    db: AsyncSession = Depends(get_db),
):
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
