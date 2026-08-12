"""Field-sales endpoints (WO 7.5): an agent's retailers, on-behalf orders,
visit notes, and basic delivery. Everything is scoped to the logged-in agent —
assignment is the security boundary."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_agent
from app.core.db import get_db
from app.models import AdminRole, User
from app.models.agent import AgentRetailer, AgentVisit, MobileGalleryItem
from app.models import Customer
from app.models.order import Order, OrderStatus
from app.models.product_serial import ProductSerial, ProductSerialStatus
from app.schemas.agent import (
    AgentOrderCreate,
    AgentOrderDetailOut,
    AgentOrderOut,
    AgentRetailerOut,
    GalleryItemOut,
    GalleryOut,
    GallerySellIn,
    VisitCreate,
    VisitOut,
)
from app.schemas.order import DeliveryProof, OrderCreate
from app.services import orders as order_service
from app.services import serials as serial_service

router = APIRouter()


async def _assigned_customer(
    db: AsyncSession, agent: User, customer_id: uuid.UUID
) -> Customer:
    """The security boundary: an agent may only act on retailers assigned to them."""
    link = await db.get(AgentRetailer, (agent.id, customer_id))
    if link is None:
        raise HTTPException(404, detail="Retailer not found")
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(404, detail="Retailer not found")
    return customer


@router.get("/retailers", response_model=list[AgentRetailerOut])
async def my_retailers(
    agent: User = Depends(require_agent), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(Customer)
            .join(AgentRetailer, AgentRetailer.customer_id == Customer.id)
            .where(AgentRetailer.agent_id == agent.id)
            .order_by(Customer.created_at)
        )
    ).scalars().all()
    out = []
    for c in rows:
        default = next((a for a in c.addresses if a.is_default), None) or (
            c.addresses[0] if c.addresses else None
        )
        out.append(
            AgentRetailerOut(
                id=c.id,
                store_name=c.store_name,
                full_name=c.full_name,
                phone=c.phone,
                province=default.province if default else None,
                city=default.city if default else None,
            )
        )
    return out


@router.post("/orders", response_model=AgentOrderDetailOut, status_code=201)
async def place_order(
    payload: AgentOrderCreate,
    agent: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """Order on behalf of an assigned retailer. Identity comes from the retailer's
    profile (server-side), items/province from the agent's form."""
    customer = await _assigned_customer(db, agent, payload.customer_id)
    create = OrderCreate(
        full_name=(customer.full_name or customer.store_name or "خرده‌فروش دیدار")[:60],
        phone=customer.phone,
        store_name=(customer.store_name or customer.full_name or "فروشگاه")[:80],
        province=payload.province,
        city=payload.city,
        contact_method="agent",
        note=payload.note,
        items=payload.items,
    )
    order = await order_service.create_order(db, create, idempotency_key=None, ip=None)
    order.agent_id = agent.id
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/orders", response_model=list[AgentOrderOut])
async def my_orders(
    agent: User = Depends(require_agent), db: AsyncSession = Depends(get_db)
):
    rows = await db.execute(
        select(Order)
        .where(Order.agent_id == agent.id)
        .order_by(Order.created_at.desc())
        .limit(100)
    )
    return rows.scalars().all()


@router.post("/orders/{order_id}/deliver", response_model=AgentOrderDetailOut)
async def deliver_order(
    order_id: uuid.UUID,
    proof: DeliveryProof,
    agent: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """ثبت تحویل پایه — the agent marks their own order delivered with proof;
    mints authenticity serials exactly like the admin path."""
    order = await db.get(Order, order_id)
    is_super = agent.role == AdminRole.superadmin  # oversight path
    if order is None or (not is_super and order.agent_id != agent.id):
        raise HTTPException(404, detail="Order not found")
    await order_service.change_status(db, order, OrderStatus.delivered)
    await serial_service.generate_for_order(db, order)
    order.delivery_assignee = agent.full_name or agent.username
    order.delivery_proof = proof.model_dump(exclude_none=True)
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/visits", response_model=VisitOut, status_code=201)
async def log_visit(
    payload: VisitCreate,
    agent: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    await _assigned_customer(db, agent, payload.customer_id)
    visit = AgentVisit(
        agent_id=agent.id, customer_id=payload.customer_id, note=payload.note
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


@router.get("/visits", response_model=list[VisitOut])
async def my_visits(
    customer_id: uuid.UUID | None = None,
    agent: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AgentVisit).where(AgentVisit.agent_id == agent.id)
    if customer_id:
        stmt = stmt.where(AgentVisit.customer_id == customer_id)
    rows = await db.execute(stmt.order_by(AgentVisit.created_at.desc()).limit(100))
    return rows.scalars().all()


# --- گالری سیار (WO 7.6): what I'm carrying + quick sale ---
def _gallery_out(i: MobileGalleryItem) -> GalleryItemOut:
    return GalleryItemOut(
        id=i.id,
        code=serial_service.format_code(i.serial.code),
        product_name=i.serial.product_name,
        image_url=i.serial.image_url,
        kind=i.kind,
        status=i.status,
        note=i.note,
        created_at=i.created_at,
    )


@router.get("/gallery", response_model=GalleryOut)
async def my_gallery(
    agent: User = Depends(require_agent), db: AsyncSession = Depends(get_db)
):
    items = (
        await db.execute(
            select(MobileGalleryItem)
            .where(MobileGalleryItem.agent_id == agent.id)
            .order_by(MobileGalleryItem.created_at.desc())
        )
    ).scalars().all()
    active = [i for i in items if i.status == "with_agent"]
    counts = {
        "with_agent": len(active),
        "sample": sum(1 for i in active if i.kind == "sample"),
        "sellable": sum(1 for i in active if i.kind == "sellable"),
        "sold": sum(1 for i in items if i.status == "sold"),
        "returned": sum(1 for i in items if i.status == "returned"),
    }
    return GalleryOut(items=[_gallery_out(i) for i in items], counts=counts)


@router.post("/gallery/{item_id}/sell", response_model=GalleryItemOut)
async def quick_sell(
    item_id: uuid.UUID,
    payload: GallerySellIn,
    agent: User = Depends(require_agent),
    db: AsyncSession = Depends(get_db),
):
    """فروش فوری در حالت محدود (WO 7.6): sell a carried sellable piece on the
    spot — the serial flips to sold with a passport event; no order row."""
    item = await db.get(MobileGalleryItem, item_id)
    if item is None or item.agent_id != agent.id:
        raise HTTPException(404, detail="Item not found")
    if item.status != "with_agent":
        raise HTTPException(409, detail="این قطعه همراه شما نیست")
    if item.kind != "sellable":
        raise HTTPException(409, detail="کالای نمونه قابل فروش نیست")
    # Row-lock the serial so two concurrent sells can't both pass the check.
    serial = (
        await db.execute(
            select(ProductSerial)
            .where(ProductSerial.id == item.serial_id)
            .with_for_update()
        )
    ).scalar_one()
    if serial.status != ProductSerialStatus.in_stock:
        raise HTTPException(409, detail="وضعیت سریال اجازه فروش نمی‌دهد")

    serial.status = ProductSerialStatus.sold
    serial_service.record_event(
        db, item.serial_id, "sold", {"quick_sale": True, "agent": agent.username}
    )
    item.status = "sold"
    if payload.note:
        item.note = payload.note
    await db.commit()
    await db.refresh(item)
    return _gallery_out(item)
