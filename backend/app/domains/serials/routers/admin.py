"""Admin serial management — thin HTTP layer over SerialQuery / SerialAction."""

import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.domains.serials.actions import SerialAction
from app.domains.serials.models import ProductSerial, ProductSerialStatus
from app.domains.serials.queries import SerialQuery
from app.domains.serials.schemas import (
    SerialGenerate,
    SerialListOut,
    SerialOut,
    SerialUpdate,
)
from app.domains.serials.services.codes import format_code
from app.domains.users import require_admin
from app.shared.validation import csv_safe

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_out(
    s: ProductSerial, verify_count: int = 0, first=None, order_reference=None
) -> SerialOut:
    return SerialOut(
        id=s.id,
        code=format_code(s.code),
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


@router.get("/serials", response_model=SerialListOut)
async def list_serials(
    serials: SerialQuery = Depends(),
    product_id: uuid.UUID | None = None,
    status: ProductSerialStatus | None = None,
    batch_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    rows, total = await serials.admin_page(
        product_id=product_id,
        status=status,
        batch_id=batch_id,
        order_id=order_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    items = [_to_out(s, cnt or 0, first, ref) for s, cnt, first, ref in rows]
    return SerialListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/serials/generate", response_model=list[SerialOut], status_code=201)
async def generate_serials(payload: SerialGenerate, action: SerialAction = Depends()):
    rows = await action.generate(payload.product_id, payload.quantity)
    return [_to_out(s) for s in rows]


@router.get("/serials/export")
async def export_serials(
    serials: SerialQuery = Depends(),
    product_id: uuid.UUID | None = None,
    status: ProductSerialStatus | None = None,
    batch_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    q: str | None = None,
):
    rows = await serials.admin_export(
        product_id=product_id, status=status, batch_id=batch_id, order_id=order_id, q=q
    )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["code", "product", "karat", "weight_grams", "status", "batch",
         "issued_at", "note"]
    )
    for s in rows:
        w.writerow([
            format_code(s.code), csv_safe(s.product_name),
            s.karat or "",
            s.weight_grams if s.weight_grams is not None else "", s.status.value,
            str(s.batch_id), s.created_at.isoformat(), csv_safe(s.note or ""),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=serials.csv"},
    )


@router.patch("/serials/{serial_id}", response_model=SerialOut)
async def update_serial(
    serial_id: uuid.UUID,
    payload: SerialUpdate,
    serials: SerialQuery = Depends(),
    action: SerialAction = Depends(),
):
    serial = await serials.by_id_or_404(serial_id, detail="Serial not found")
    return _to_out(await action.update_admin(serial, payload))


@router.delete("/serials/{serial_id}", status_code=204)
async def delete_serial(
    serial_id: uuid.UUID,
    serials: SerialQuery = Depends(),
    action: SerialAction = Depends(),
):
    serial = await serials.by_id_or_404(serial_id, detail="Serial not found")
    await action.delete(serial)
