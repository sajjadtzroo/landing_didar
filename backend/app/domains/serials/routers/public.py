"""Public serial-passport routes: authenticity verify, QR label, warranty
activation and buyback requests.

Thin HTTP layer over SerialQuery / WarrantyQuery / BuybackQuery and the
serial/warranty/buyback actions; registered with tags=["public"] so OpenAPI
is unchanged."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import get_client_ip
from app.domains.orders import hash_ip
from app.domains.serials.actions import (
    ActivateWarrantyAction,
    BuybackAction,
    SerialAction,
)
from app.domains.serials.models import BuybackStatus
from app.domains.serials.queries import BuybackQuery, SerialQuery, WarrantyQuery
from app.domains.serials.schemas import (
    BuybackCreate,
    BuybackCreatedOut,
    SerialEventOut,
    SerialVerifyOut,
    WarrantyActivate,
    WarrantyState,
)
from app.domains.serials.services.codes import format_code, qr_png

router = APIRouter()


@router.get("/serials/verify", response_model=SerialVerifyOut)
@limiter.limit("30/minute")
async def verify_serial(
    request: Request,
    code: str,
    response: Response,
    serials: SerialQuery = Depends(),
    warranties: WarrantyQuery = Depends(),
    buybacks: BuybackQuery = Depends(),
    action: SerialAction = Depends(),
):
    """Public authenticity check. The hand-typed code is normalized, then looked up.
    Unknown AND revoked codes return the SAME opaque 404 (a revoked code is not
    authentic). Every hit is logged as the copy-attack signal. Never cached, and
    rate-limited so valid codes can't be enumerated/scraped."""
    response.headers["Cache-Control"] = "no-store"
    serial = await serials.verifiable_by_code(code)
    await action.log_scan(serial.id, hash_ip(get_client_ip(request)))
    stored = await serials.public_events(serial.id)
    events = [SerialEventOut(type="minted", at=serial.created_at)] + [
        SerialEventOut(type=e.type, at=e.created_at) for e in stored
    ]

    # Warranty state (WO 7.8) — status only, no PII.
    w, warranty_available = await warranties.passport_state(serial)
    warranty = (
        WarrantyState(
            started_at=w.started_at,
            expires_at=w.expires_at,
            active=datetime.now(UTC) < w.expires_at,
        )
        if w
        else None
    )

    # Latest buyback status, if any (WO 7.9).
    bb = await buybacks.latest_status(serial.id)

    return SerialVerifyOut(
        code=format_code(serial.code),
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


@router.post("/serials/{code}/warranty", response_model=WarrantyState, status_code=201)
@limiter.limit("10/hour")
async def activate_warranty(
    request: Request,
    code: str,
    payload: WarrantyActivate,
    serials: SerialQuery = Depends(),
    activate: ActivateWarrantyAction = Depends(),
):
    """فعال‌سازی گارانتی (WO 7.8): only for a sold, warrantable piece without an
    existing warranty. 12 months from activation."""
    serial = await serials.sold_by_code(code)
    warranty = await activate.execute(serial, payload)
    return WarrantyState(
        started_at=warranty.started_at, expires_at=warranty.expires_at, active=True
    )


@router.post(
    "/serials/{code}/buyback", response_model=BuybackCreatedOut, status_code=201
)
@limiter.limit("5/hour")
async def request_buyback(
    request: Request,
    code: str,
    payload: BuybackCreate,
    serials: SerialQuery = Depends(),
    action: BuybackAction = Depends(),
):
    """ثبت درخواست بازخرید (WO 7.9). One open request per piece at a time."""
    serial = await serials.sold_by_code(code)
    await action.request(serial, payload)
    return BuybackCreatedOut(status=BuybackStatus.under_review)


@router.get("/serials/{code}/qr.png")
@limiter.limit("60/minute")
async def serial_qr(request: Request, code: str, serials: SerialQuery = Depends()):
    """QR label image for a code — encodes the public /verify deep-link. You must
    already know the full code, so this exposes nothing new (404 for unknown)."""
    serial = await serials.by_code(code)
    if serial is None:
        raise HTTPException(404, detail="Not found")
    # PNG encode is CPU work — keep it off the event loop
    png = await asyncio.to_thread(qr_png, serial.code, settings.cors_origins[0])
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
