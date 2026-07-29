import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.order import Order, OrderStatus
from app.schemas.order import (
    OrderDetailOut,
    OrderListOut,
    OrderUpdate,
)
from app.services import orders as order_service

router = APIRouter(dependencies=[Depends(require_admin)])


def _apply_filters(
    stmt,
    status: OrderStatus | None,
    province: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    q: str | None,
):
    if status:
        stmt = stmt.where(Order.status == status)
    if province:
        stmt = stmt.where(Order.province == province)
    if date_from:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.created_at <= date_to)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Order.full_name.ilike(like),
                Order.phone.ilike(like),
                Order.store_name.ilike(like),
            )
        )
    return stmt


@router.get("/orders", response_model=OrderListOut)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    status: OrderStatus | None = None,
    province: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    base = _apply_filters(select(Order), status, province, date_from, date_to, q)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    unread = await db.scalar(
        select(func.count()).select_from(Order).where(~Order.is_read)
    )
    rows = await db.execute(
        base.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return OrderListOut(
        items=list(rows.scalars().all()),
        total=total or 0,
        page=page,
        page_size=page_size,
        unread=unread or 0,
    )


@router.get("/orders/export")
async def export_orders(
    db: AsyncSession = Depends(get_db),
    status: OrderStatus | None = None,
    province: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
):
    stmt = _apply_filters(select(Order), status, province, date_from, date_to, q)
    rows = (await db.execute(stmt.order_by(Order.created_at.desc()))).scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["reference", "date", "name", "phone", "store", "province", "city",
         "status", "total", "items", "source"]
    )
    for o in rows:
        items = "; ".join(f"{i.product_name} x{i.quantity}" for i in o.items)
        w.writerow(
            [o.reference, o.created_at.isoformat(), o.full_name, o.phone,
             o.store_name, o.province, o.city or "", o.status.value,
             int(o.total), items, o.utm_source or ""]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )


@router.get("/orders/{order_id}", response_model=OrderDetailOut)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}", response_model=OrderDetailOut)
async def update_order(
    order_id: str, payload: OrderUpdate, db: AsyncSession = Depends(get_db)
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    if payload.status is not None:
        await order_service.change_status(db, order, payload.status)
    if payload.internal_note is not None:
        order.internal_note = payload.internal_note
    if payload.is_read is not None:
        order.is_read = payload.is_read
    await db.commit()
    await db.refresh(order)
    return order
