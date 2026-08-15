"""Admin order management — thin HTTP layer over OrderQuery / OrderAction."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.domains.orders.actions import OrderAction
from app.domains.orders.models import OrderStatus
from app.domains.orders.queries import OrderQuery
from app.domains.orders.schemas import OrderDetailOut, OrderListOut, OrderUpdate
from app.domains.users import require_admin
from app.shared.validation import csv_safe

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/orders", response_model=OrderListOut)
async def list_orders(
    orders: OrderQuery = Depends(),
    status: OrderStatus | None = None,
    province: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
    sort: str = "created_at",
    dir: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = orders.admin_filter(
        status=status, province=province, date_from=date_from, date_to=date_to, q=q
    )
    items, total = await orders.page(
        stmt,
        page=page,
        page_size=page_size,
        order_by=orders.admin_order_by(sort, dir),
    )
    return OrderListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        unread=await orders.unread_count(),
    )


@router.get("/orders/export")
async def export_orders(
    orders: OrderQuery = Depends(),
    status: OrderStatus | None = None,
    province: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    q: str | None = None,
):
    rows = await orders.admin_export(
        status=status, province=province, date_from=date_from, date_to=date_to, q=q
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["reference", "date", "name", "phone", "store", "province", "city",
         "contact_method", "status", "total", "items", "source"]
    )
    for o in rows:
        items = "; ".join(f"{i.product_name} x{i.quantity}" for i in o.items)
        w.writerow(
            [o.reference, o.created_at.isoformat(), csv_safe(o.full_name), o.phone,
             csv_safe(o.store_name), o.province, csv_safe(o.city or ""),
             o.contact_method.value, o.status.value, int(o.total),
             csv_safe(items), csv_safe(o.utm_source or "")]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )


@router.get("/orders/{order_id}", response_model=OrderDetailOut)
async def get_order(order_id: str, orders: OrderQuery = Depends()):
    return await orders.by_id_or_404(order_id, detail="Order not found")


@router.patch("/orders/{order_id}", response_model=OrderDetailOut)
async def update_order(
    order_id: str,
    payload: OrderUpdate,
    orders: OrderQuery = Depends(),
    action: OrderAction = Depends(),
):
    order = await orders.by_id_or_404(order_id, detail="Order not found")
    return await action.update_admin(order, payload)


@router.post("/orders/{order_id}/generate-serials")
async def generate_order_serials(
    order_id: str,
    orders: OrderQuery = Depends(),
    action: OrderAction = Depends(),
):
    """Manual fallback: mint serials for an order (e.g. delivered before this feature).
    Idempotent — returns the order's codes whether it minted now or already had them."""
    order = await orders.by_id_or_404(order_id, detail="Order not found")
    return {"codes": await action.mint_serials(order)}
