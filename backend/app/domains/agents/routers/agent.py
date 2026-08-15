"""Field-sales endpoints (WO 7.5): an agent's retailers, on-behalf orders,
visit notes, and basic delivery. Everything is scoped to the logged-in agent —
assignment is the security boundary."""

import uuid

from fastapi import APIRouter, Depends

from app.domains.agents.actions import AgentOrderAction, AgentVisitAction, GalleryAction
from app.domains.agents.models import MobileGalleryItem
from app.domains.agents.queries import (
    AgentOrderQuery,
    AgentRetailerQuery,
    AgentVisitQuery,
    GalleryQuery,
)
from app.domains.agents.schemas import (
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
from app.domains.orders import DeliveryProof
from app.domains.serials import service as serial_service
from app.domains.users import User, require_agent

router = APIRouter()


@router.get("/retailers", response_model=list[AgentRetailerOut])
async def my_retailers(
    agent: User = Depends(require_agent),
    retailers: AgentRetailerQuery = Depends(),
):
    rows = await retailers.assigned_customers(agent.id)
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
    retailers: AgentRetailerQuery = Depends(),
    action: AgentOrderAction = Depends(),
):
    """Order on behalf of an assigned retailer. Identity comes from the retailer's
    profile (server-side), items/province from the agent's form."""
    customer = await retailers.assigned_customer_or_404(agent.id, payload.customer_id)
    return await action.place_for_retailer(agent, customer, payload)


@router.get("/orders", response_model=list[AgentOrderOut])
async def my_orders(
    agent: User = Depends(require_agent), orders: AgentOrderQuery = Depends()
):
    return await orders.for_agent(agent.id)


@router.post("/orders/{order_id}/deliver", response_model=AgentOrderDetailOut)
async def deliver_order(
    order_id: uuid.UUID,
    proof: DeliveryProof,
    agent: User = Depends(require_agent),
    orders: AgentOrderQuery = Depends(),
    action: AgentOrderAction = Depends(),
):
    """ثبت تحویل پایه — the agent marks their own order delivered with proof;
    mints authenticity serials exactly like the admin path."""
    order = await orders.owned_or_404(order_id, agent)
    return await action.deliver(order, agent, proof)


@router.post("/visits", response_model=VisitOut, status_code=201)
async def log_visit(
    payload: VisitCreate,
    agent: User = Depends(require_agent),
    retailers: AgentRetailerQuery = Depends(),
    action: AgentVisitAction = Depends(),
):
    await retailers.assigned_customer_or_404(agent.id, payload.customer_id)
    return await action.log(agent.id, payload)


@router.get("/visits", response_model=list[VisitOut])
async def my_visits(
    customer_id: uuid.UUID | None = None,
    agent: User = Depends(require_agent),
    visits: AgentVisitQuery = Depends(),
):
    return await visits.for_agent(agent.id, customer_id)


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
    agent: User = Depends(require_agent), gallery: GalleryQuery = Depends()
):
    items = await gallery.for_agent(agent.id)
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
    gallery: GalleryQuery = Depends(),
    action: GalleryAction = Depends(),
):
    """فروش فوری در حالت محدود (WO 7.6): sell a carried sellable piece on the
    spot — the serial flips to sold with a passport event; no order row."""
    item = await gallery.owned_or_404(item_id, agent.id)
    return _gallery_out(await action.quick_sell(item, agent, payload))
