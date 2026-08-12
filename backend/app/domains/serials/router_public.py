"""Public serial-passport routes: authenticity verify, QR label, warranty
activation and buyback requests.

Moved verbatim from app/api/v1/public.py during the domain migration;
registered with tags=["public"] so OpenAPI is unchanged."""

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip
from app.api.limiter import limiter
from app.core.config import settings
from app.core.db import get_db
from app.domains.catalog import Product
from app.domains.orders import hash_ip
from app.domains.serials import service as serial_service
from app.domains.serials.serial_models import (
    ProductSerial,
    ProductSerialStatus,
    SerialEvent,
)
from app.domains.serials.serial_schemas import (
    SerialEventOut,
    SerialVerifyOut,
    WarrantyState,
)
from app.domains.serials.warranty_models import (
    BuybackRequest,
    BuybackStatus,
    Warranty,
)
from app.domains.serials.warranty_schemas import (
    BuybackCreate,
    BuybackCreatedOut,
    WarrantyActivate,
)

router = APIRouter()


@router.get("/serials/verify", response_model=SerialVerifyOut)
@limiter.limit("30/minute")
async def verify_serial(
    request: Request,
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Public authenticity check. The hand-typed code is normalized, then looked up.
    Unknown AND revoked codes return the SAME opaque 404 (a revoked code is not
    authentic). Every hit is logged as the copy-attack signal. Never cached, and
    rate-limited so valid codes can't be enumerated/scraped."""
    response.headers["Cache-Control"] = "no-store"
    normalized = serial_service.normalize(code)
    if not normalized:
        raise HTTPException(404, detail="Not found")
    serial = (
        await db.execute(
            select(ProductSerial).where(ProductSerial.code == normalized)
        )
    ).scalar_one_or_none()
    if serial is None or serial.status == ProductSerialStatus.revoked:
        raise HTTPException(404, detail="Not found")
    await serial_service.log_scan(db, serial.id, hash_ip(get_client_ip(request)))
    # Passport timeline: mint is derived (created_at); public transitions only.
    _PUBLIC_EVENTS = ("sold", "warranty_activated", "buyback_requested")
    stored = (
        await db.execute(
            select(SerialEvent)
            .where(SerialEvent.serial_id == serial.id, SerialEvent.type.in_(_PUBLIC_EVENTS))
            .order_by(SerialEvent.created_at)
        )
    ).scalars().all()
    events = [SerialEventOut(type="minted", at=serial.created_at)] + [
        SerialEventOut(type=e.type, at=e.created_at) for e in stored
    ]

    # Warranty state (WO 7.8) — status only, no PII.
    now = datetime.now(UTC)
    w = (
        await db.execute(select(Warranty).where(Warranty.serial_id == serial.id))
    ).scalar_one_or_none()
    warranty = (
        WarrantyState(started_at=w.started_at, expires_at=w.expires_at, active=now < w.expires_at)
        if w
        else None
    )
    warranty_available = False
    if w is None and serial.status == ProductSerialStatus.sold:
        product = await db.get(Product, serial.product_id)
        warranty_available = bool(product and product.warrantable)

    # Latest buyback status, if any (WO 7.9).
    bb = (
        await db.execute(
            select(BuybackRequest.status)
            .where(BuybackRequest.serial_id == serial.id)
            .order_by(BuybackRequest.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return SerialVerifyOut(
        code=serial_service.format_code(serial.code),
        product_name=serial.product_name,
        karat=serial.karat,
        weight_grams=serial.weight_grams,
        image_url=serial.image_url,
        issued_at=serial.created_at,
        events=events,
        warranty=warranty,
        warranty_available=warranty_available,
        buyback_status=bb.value if bb else None,
    )


async def _sold_serial_or_404(db: AsyncSession, code: str) -> ProductSerial:
    """Warranty/buyback both require a genuine, SOLD piece: 404 for unknown or
    revoked (opaque), 409 for a piece still in stock."""
    normalized = serial_service.normalize(code)
    serial = (
        await db.execute(select(ProductSerial).where(ProductSerial.code == normalized))
    ).scalar_one_or_none() if normalized else None
    if serial is None or serial.status == ProductSerialStatus.revoked:
        raise HTTPException(404, detail="Not found")
    if serial.status != ProductSerialStatus.sold:
        raise HTTPException(409, detail="این قطعه هنوز فروخته نشده است")
    return serial


@router.post("/serials/{code}/warranty", response_model=WarrantyState, status_code=201)
@limiter.limit("10/hour")
async def activate_warranty(
    request: Request,
    code: str,
    payload: WarrantyActivate,
    db: AsyncSession = Depends(get_db),
):
    """فعال‌سازی گارانتی (WO 7.8): only for a sold, warrantable piece without an
    existing warranty. 12 months from activation."""
    serial = await _sold_serial_or_404(db, code)
    product = await db.get(Product, serial.product_id)
    if not (product and product.warrantable):
        raise HTTPException(409, detail="این محصول مشمول گارانتی نیست")
    existing = (
        await db.execute(select(Warranty).where(Warranty.serial_id == serial.id))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, detail="گارانتی این قطعه قبلاً فعال شده است")

    now = datetime.now(UTC)
    warranty = Warranty(
        serial_id=serial.id,
        customer_name=payload.full_name,
        customer_phone=payload.phone,
        started_at=now,
        expires_at=now + timedelta(days=365),
    )
    db.add(warranty)
    serial_service.record_event(db, serial.id, "warranty_activated")
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent activation won the race on the serial_id unique constraint.
        await db.rollback()
        raise HTTPException(409, detail="گارانتی این قطعه قبلاً فعال شده است")
    return WarrantyState(started_at=now, expires_at=warranty.expires_at, active=True)


@router.post("/serials/{code}/buyback", response_model=BuybackCreatedOut, status_code=201)
@limiter.limit("5/hour")
async def request_buyback(
    request: Request,
    code: str,
    payload: BuybackCreate,
    db: AsyncSession = Depends(get_db),
):
    """ثبت درخواست بازخرید (WO 7.9). One open request per piece at a time."""
    serial = await _sold_serial_or_404(db, code)
    open_req = (
        await db.execute(
            select(BuybackRequest.id).where(
                BuybackRequest.serial_id == serial.id,
                BuybackRequest.status == BuybackStatus.under_review,
            )
        )
    ).scalar_one_or_none()
    if open_req:
        raise HTTPException(409, detail="برای این قطعه یک درخواست در حال بررسی وجود دارد")
    req = BuybackRequest(
        serial_id=serial.id,
        requester_name=payload.full_name,
        requester_phone=payload.phone,
        note=payload.note,
    )
    db.add(req)
    serial_service.record_event(db, serial.id, "buyback_requested")
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent request won the race on the partial-unique open-request index.
        await db.rollback()
        raise HTTPException(409, detail="برای این قطعه یک درخواست در حال بررسی وجود دارد")
    return BuybackCreatedOut(status=BuybackStatus.under_review)


@router.get("/serials/{code}/qr.png")
@limiter.limit("60/minute")
async def serial_qr(
    request: Request, code: str, db: AsyncSession = Depends(get_db)
):
    """QR label image for a code — encodes the public /verify deep-link. You must
    already know the full code, so this exposes nothing new (404 for unknown)."""
    normalized = serial_service.normalize(code)
    exists = normalized and (
        await db.execute(
            select(ProductSerial.id).where(ProductSerial.code == normalized)
        )
    ).scalar_one_or_none()
    if not exists:
        raise HTTPException(404, detail="Not found")
    # PNG encode is CPU work — keep it off the event loop
    png = await asyncio.to_thread(serial_service.qr_png, normalized, settings.cors_origins[0])
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
