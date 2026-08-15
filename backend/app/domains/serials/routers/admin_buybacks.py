"""Admin buyback review — thin HTTP layer over BuybackQuery / BuybackAction."""

import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.domains.serials.actions import BuybackAction
from app.domains.serials.models import BuybackRequest, BuybackStatus, ProductSerial
from app.domains.serials.queries import BuybackQuery, SerialQuery
from app.domains.serials.schemas import BuybackListOut, BuybackOut, BuybackUpdate
from app.domains.serials.services.codes import format_code
from app.domains.users import require_admin
from app.shared.validation import csv_safe

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_out(b: BuybackRequest, s: ProductSerial) -> BuybackOut:
    return BuybackOut(
        id=b.id,
        serial_id=b.serial_id,
        code=format_code(s.code),
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
    buybacks: BuybackQuery = Depends(),
    status: BuybackStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rows, total = await buybacks.admin_page(
        status=status, page=page, page_size=page_size
    )
    items = [_to_out(b, s) for b, s in rows]
    return BuybackListOut(items=items, total=total, page=page, page_size=page_size)


@router.patch("/buybacks/{buyback_id}", response_model=BuybackOut)
async def update_buyback(
    buyback_id: uuid.UUID,
    payload: BuybackUpdate,
    buybacks: BuybackQuery = Depends(),
    serials: SerialQuery = Depends(),
    action: BuybackAction = Depends(),
):
    b = await buybacks.by_id_or_404(buyback_id, detail="Buyback request not found")
    b = await action.update_admin(b, payload)
    s = await serials.by_id(b.serial_id)
    return _to_out(b, s)


@router.get("/buybacks/export")
async def export_buybacks(
    buybacks: BuybackQuery = Depends(), status: BuybackStatus | None = None
):
    """خروجی برای عملیات داخلی / ثبت مالی (WO 7.9)."""
    rows = await buybacks.admin_export(status)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["code", "product", "requester", "phone", "status", "offered_price",
         "note", "admin_note", "created_at"]
    )
    for b, s in rows:
        w.writerow([
            format_code(s.code), csv_safe(s.product_name), csv_safe(b.requester_name),
            b.requester_phone, b.status.value,
            b.offered_price if b.offered_price is not None else "",
            csv_safe(b.note or ""), csv_safe(b.admin_note or ""),
            b.created_at.isoformat(),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=buybacks.csv"},
    )
