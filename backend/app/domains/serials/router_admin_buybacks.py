import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.domains.serials import service as serial_service
from app.domains.serials.serial_models import ProductSerial
from app.domains.serials.warranty_models import BuybackRequest, BuybackStatus
from app.domains.serials.warranty_schemas import (
    BuybackListOut,
    BuybackOut,
    BuybackUpdate,
)

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_out(b: BuybackRequest, s: ProductSerial) -> BuybackOut:
    return BuybackOut(
        id=b.id,
        serial_id=b.serial_id,
        code=serial_service.format_code(s.code),
        product_name=s.product_name,
        requester_name=b.requester_name,
        requester_phone=b.requester_phone,
        note=b.note,
        status=b.status,
        offered_price=b.offered_price,
        admin_note=b.admin_note,
        created_at=b.created_at,
    )


@router.get("/buybacks", response_model=BuybackListOut)
async def list_buybacks(
    db: AsyncSession = Depends(get_db),
    status: BuybackStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    base = select(BuybackRequest, ProductSerial).join(
        ProductSerial, ProductSerial.id == BuybackRequest.serial_id
    )
    count = select(func.count()).select_from(BuybackRequest)
    if status:
        base = base.where(BuybackRequest.status == status)
        count = count.where(BuybackRequest.status == status)
    total = await db.scalar(count)
    rows = await db.execute(
        base.order_by(BuybackRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_out(b, s) for b, s in rows.all()]
    return BuybackListOut(items=items, total=total or 0, page=page, page_size=page_size)


@router.patch("/buybacks/{buyback_id}", response_model=BuybackOut)
async def update_buyback(
    buyback_id: uuid.UUID, payload: BuybackUpdate, db: AsyncSession = Depends(get_db)
):
    b = await db.get(BuybackRequest, buyback_id)
    if b is None:
        raise HTTPException(404, detail="Buyback request not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    await db.commit()
    await db.refresh(b)
    s = await db.get(ProductSerial, b.serial_id)
    return _to_out(b, s)


@router.get("/buybacks/export")
async def export_buybacks(
    db: AsyncSession = Depends(get_db), status: BuybackStatus | None = None
):
    """خروجی برای عملیات داخلی / ثبت مالی (WO 7.9)."""
    stmt = select(BuybackRequest, ProductSerial).join(
        ProductSerial, ProductSerial.id == BuybackRequest.serial_id
    )
    if status:
        stmt = stmt.where(BuybackRequest.status == status)
    rows = (await db.execute(stmt.order_by(BuybackRequest.created_at.desc()))).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["code", "product", "requester", "phone", "status", "offered_price", "note", "admin_note", "created_at"])
    for b, s in rows:
        safe = serial_service.csv_safe
        w.writerow([
            serial_service.format_code(s.code), safe(s.product_name), safe(b.requester_name),
            b.requester_phone, b.status.value,
            b.offered_price if b.offered_price is not None else "",
            safe(b.note or ""), safe(b.admin_note or ""), b.created_at.isoformat(),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=buybacks.csv"},
    )
