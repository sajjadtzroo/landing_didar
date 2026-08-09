"""گالری سیار admin side (WO 7.6): hand pieces to an agent, take them back,
and see what each agent is carrying."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.agent import MobileGalleryItem
from app.models.product import Product
from app.models.product_serial import ProductSerial, ProductSerialStatus
from app.models.user import AdminRole, User
from app.schemas.agent import GalleryAssignIn, GalleryItemOut, GalleryOut
from app.services import serials as serial_service

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_out(i: MobileGalleryItem) -> GalleryItemOut:
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
async def gallery_agents(db: AsyncSession = Depends(get_db)):
    """Active agent accounts for the picker (admin-level; /admin/users is
    superadmin-only by design)."""
    rows = (
        await db.execute(
            select(User).where(User.role == AdminRole.agent, User.is_active)
            .order_by(User.created_at)
        )
    ).scalars().all()
    return [{"id": str(u.id), "username": u.username, "full_name": u.full_name} for u in rows]


@router.get("/mobile-gallery", response_model=GalleryOut)
async def list_gallery(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    items = (
        await db.execute(
            select(MobileGalleryItem)
            .where(MobileGalleryItem.agent_id == agent_id)
            .order_by(MobileGalleryItem.created_at.desc())
        )
    ).scalars().all()
    return GalleryOut(items=[_to_out(i) for i in items], counts=_counts(items))


@router.post("/mobile-gallery", response_model=GalleryItemOut, status_code=201)
async def assign_item(payload: GalleryAssignIn, db: AsyncSession = Depends(get_db)):
    """تحویل اولیه کالا به ایجنت: an in-stock serial goes into the agent's bag."""
    agent = await db.get(User, payload.agent_id)
    if agent is None or agent.role != AdminRole.agent:
        raise HTTPException(404, detail="Agent not found")

    normalized = serial_service.normalize(payload.code)
    serial = (
        await db.execute(select(ProductSerial).where(ProductSerial.code == normalized))
    ).scalar_one_or_none()
    if serial is None:
        raise HTTPException(404, detail="سریال یافت نشد")
    if serial.status != ProductSerialStatus.in_stock:
        raise HTTPException(409, detail="فقط سریال‌های موجود (فروخته‌نشده) قابل تحویل‌اند")
    active = (
        await db.execute(
            select(MobileGalleryItem.id).where(
                MobileGalleryItem.serial_id == serial.id,
                MobileGalleryItem.status == "with_agent",
            )
        )
    ).scalar_one_or_none()
    if active:
        raise HTTPException(409, detail="این قطعه هم‌اکنون همراه یک ایجنت است")

    kind = payload.kind
    if kind is None:
        product = await db.get(Product, serial.product_id)
        kind = "sample" if (product and product.product_status == "sample") else "sellable"

    item = MobileGalleryItem(
        agent_id=payload.agent_id, serial_id=serial.id, kind=kind, note=payload.note
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _to_out(item)


@router.patch("/mobile-gallery/{item_id}/return", response_model=GalleryItemOut)
async def return_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """ثبت برگشت ساده: the piece is physically back at the office."""
    item = await db.get(MobileGalleryItem, item_id)
    if item is None:
        raise HTTPException(404, detail="Item not found")
    if item.status != "with_agent":
        raise HTTPException(409, detail="این قطعه همراه ایجنت نیست")
    item.status = "returned"
    await db.commit()
    await db.refresh(item)
    return _to_out(item)
