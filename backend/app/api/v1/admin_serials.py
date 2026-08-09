import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.order import Order
from app.models.product import Product
from app.models.product_serial import ProductSerial, ProductSerialStatus, SerialScan
from app.schemas.serial import SerialGenerate, SerialListOut, SerialOut, SerialUpdate
from app.services import serials as serial_service

router = APIRouter(dependencies=[Depends(require_admin)])


def _apply_filters(stmt, product_id, status, batch_id, order_id, q):
    if product_id:
        stmt = stmt.where(ProductSerial.product_id == product_id)
    if status:
        stmt = stmt.where(ProductSerial.status == status)
    if batch_id:
        stmt = stmt.where(ProductSerial.batch_id == batch_id)
    if order_id:
        stmt = stmt.where(ProductSerial.order_id == order_id)
    if q:
        norm = serial_service.normalize(q)
        if norm:
            # Prefix match — index-friendly (unlike %q%).
            stmt = stmt.where(ProductSerial.code.like(f"{norm}%"))
    return stmt


def _to_out(s: ProductSerial, verify_count: int = 0, first=None, order_reference=None) -> SerialOut:
    return SerialOut(
        id=s.id,
        code=serial_service.format_code(s.code),
        product_id=s.product_id,
        product_name=s.product_name,
        karat=s.karat,
        weight_grams=s.weight_grams,
        status=s.status,
        batch_id=s.batch_id,
        note=s.note,
        created_at=s.created_at,
        order_reference=order_reference,
        verify_count=verify_count,
        first_verified_at=first,
    )


def _scan_agg():
    return (
        select(
            SerialScan.serial_id.label("sid"),
            func.count().label("cnt"),
            func.min(SerialScan.created_at).label("first"),
        )
        .group_by(SerialScan.serial_id)
        .subquery()
    )


@router.get("/serials", response_model=SerialListOut)
async def list_serials(
    db: AsyncSession = Depends(get_db),
    product_id: uuid.UUID | None = None,
    status: ProductSerialStatus | None = None,
    batch_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    agg = _scan_agg()
    base = (
        select(ProductSerial, agg.c.cnt, agg.c.first, Order.reference)
        .outerjoin(agg, agg.c.sid == ProductSerial.id)
        .outerjoin(Order, Order.id == ProductSerial.order_id)
    )
    base = _apply_filters(base, product_id, status, batch_id, order_id, q)

    count_stmt = _apply_filters(
        select(ProductSerial.id), product_id, status, batch_id, order_id, q
    )
    total = await db.scalar(select(func.count()).select_from(count_stmt.subquery()))

    rows = await db.execute(
        base.order_by(ProductSerial.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_out(s, cnt or 0, first, ref) for s, cnt, first, ref in rows.all()]
    return SerialListOut(items=items, total=total or 0, page=page, page_size=page_size)


@router.post("/serials/generate", response_model=list[SerialOut], status_code=201)
async def generate_serials(payload: SerialGenerate, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(404, detail="Product not found")
    batch_id = uuid.uuid4()
    rows = await serial_service.generate(db, product, payload.quantity, batch_id)
    return [_to_out(s) for s in rows]


@router.get("/serials/export")
async def export_serials(
    db: AsyncSession = Depends(get_db),
    product_id: uuid.UUID | None = None,
    status: ProductSerialStatus | None = None,
    batch_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    q: str | None = None,
):
    stmt = _apply_filters(select(ProductSerial), product_id, status, batch_id, order_id, q)
    rows = (await db.execute(stmt.order_by(ProductSerial.created_at.desc()))).scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["code", "product", "karat", "weight_grams", "status", "batch", "issued_at", "note"])
    for s in rows:
        w.writerow([
            serial_service.format_code(s.code), s.product_name, s.karat or "",
            s.weight_grams if s.weight_grams is not None else "", s.status.value,
            str(s.batch_id), s.created_at.isoformat(), s.note or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=serials.csv"},
    )


@router.patch("/serials/{serial_id}", response_model=SerialOut)
async def update_serial(
    serial_id: uuid.UUID, payload: SerialUpdate, db: AsyncSession = Depends(get_db)
):
    serial = await db.get(ProductSerial, serial_id)
    if serial is None:
        raise HTTPException(404, detail="Serial not found")
    old_status = serial.status
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(serial, k, v)
    # Passport timeline: log the transition (back to in_stock reads as "restored").
    if serial.status != old_status:
        type_ = (
            "restored"
            if serial.status == ProductSerialStatus.in_stock
            else serial.status.value
        )
        serial_service.record_event(db, serial.id, type_, {"from": old_status.value})
    await db.commit()
    await db.refresh(serial)
    return _to_out(serial)


@router.delete("/serials/{serial_id}", status_code=204)
async def delete_serial(serial_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    serial = await db.get(ProductSerial, serial_id)
    if serial is None:
        raise HTTPException(404, detail="Serial not found")
    await db.delete(serial)
    await db.commit()
