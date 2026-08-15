"""گالری سیار admin side (WO 7.6): hand pieces to an agent, take them back,
and see what each agent is carrying."""

import uuid

from fastapi import APIRouter, Depends

from app.domains.agents.actions import GalleryAction
from app.domains.agents.models import MobileGalleryItem
from app.domains.agents.queries import GalleryQuery
from app.domains.agents.schemas import GalleryAssignIn, GalleryItemOut, GalleryOut
from app.domains.serials import format_code
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_out(i: MobileGalleryItem) -> GalleryItemOut:
    return GalleryItemOut(
        id=i.id,
        code=format_code(i.serial.code),
        product_name=i.serial.product_name,
        image_url=i.serial.image_url,
        kind=i.kind,
        status=i.status,
        note=i.note,
        created_at=i.created_at,
    )


def _counts(items: list[MobileGalleryItem]) -> dict[str, int]:
    active = [i for i in items if i.status == "with_agent"]
    return {
        "with_agent": len(active),
        "sample": sum(1 for i in active if i.kind == "sample"),
        "sellable": sum(1 for i in active if i.kind == "sellable"),
        "sold": sum(1 for i in items if i.status == "sold"),
        "returned": sum(1 for i in items if i.status == "returned"),
    }


@router.get("/mobile-gallery/agents")
async def gallery_agents(gallery: GalleryQuery = Depends()):
    """Active agent accounts for the picker (admin-level; /admin/users is
    superadmin-only by design)."""
    rows = await gallery.active_agents()
    return [
        {"id": str(u.id), "username": u.username, "full_name": u.full_name}
        for u in rows
    ]


@router.get("/mobile-gallery", response_model=GalleryOut)
async def list_gallery(agent_id: uuid.UUID, gallery: GalleryQuery = Depends()):
    items = await gallery.for_agent(agent_id)
    return GalleryOut(items=[_to_out(i) for i in items], counts=_counts(items))


@router.post("/mobile-gallery", response_model=GalleryItemOut, status_code=201)
async def assign_item(payload: GalleryAssignIn, action: GalleryAction = Depends()):
    """تحویل اولیه کالا به ایجنت: an in-stock serial goes into the agent's bag."""
    return _to_out(await action.assign(payload))


@router.patch("/mobile-gallery/{item_id}/return", response_model=GalleryItemOut)
async def return_item(
    item_id: uuid.UUID,
    gallery: GalleryQuery = Depends(),
    action: GalleryAction = Depends(),
):
    """ثبت برگشت ساده: the piece is physically back at the office."""
    item = await gallery.by_id_or_404(item_id, detail="Item not found")
    return _to_out(await action.return_item(item))
