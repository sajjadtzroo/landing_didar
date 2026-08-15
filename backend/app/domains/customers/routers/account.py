"""Customer account panel: phone-OTP login + orders, favorites, addresses, profile.

Session is a signed cookie (didar_customer), mirroring the admin auth scheme with
a different salt. Orders are linked to a customer by matching phone, so purchases
made before signup still show up.
"""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Request,
    Response,
    UploadFile,
)

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import CUSTOMER_COOKIE, issue_customer_session
from app.domains.catalog import ProductOut
from app.domains.customers.actions import (
    AddressAction,
    CustomerAction,
    FavoriteAction,
    RequestOtpAction,
    VerifyOtpAction,
)
from app.domains.customers.dependencies import require_customer
from app.domains.customers.queries import AddressQuery, CustomerQuery, FavoriteQuery
from app.domains.customers.schemas import (
    AddressIn,
    AddressOut,
    AddressUpdate,
    CustomerOut,
    CustomerUpdate,
    OtpRequestIn,
    OtpRequestOut,
    OtpVerifyIn,
)
from app.domains.orders import OrderTrackOut

router = APIRouter()


def _set_customer_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CUSTOMER_COOKIE,
        token,
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


# --- Auth ---------------------------------------------------------------------
@router.post("/otp/request", response_model=OtpRequestOut)
@limiter.limit("5/hour")
async def request_otp(
    request: Request, payload: OtpRequestIn, otp: RequestOtpAction = Depends()
):
    return OtpRequestOut(sent=True, dev_code=await otp.execute(payload.phone))


@router.post("/otp/verify", response_model=CustomerOut)
@limiter.limit("10/minute")
async def verify_otp_code(
    request: Request,
    payload: OtpVerifyIn,
    response: Response,
    verify: VerifyOtpAction = Depends(),
):
    customer = await verify.execute(payload.phone, payload.code)
    _set_customer_cookie(response, issue_customer_session(str(customer.id)))
    return customer


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(CUSTOMER_COOKIE, path="/")
    return {"detail": "ok"}


@router.get("/me", response_model=CustomerOut)
async def me(
    customer_id: uuid.UUID = Depends(require_customer),
    customers: CustomerQuery = Depends(),
):
    return await customers.current(customer_id)


@router.patch("/me", response_model=CustomerOut)
async def update_me(
    payload: CustomerUpdate,
    customer_id: uuid.UUID = Depends(require_customer),
    customers: CustomerQuery = Depends(),
    action: CustomerAction = Depends(),
):
    c = await customers.current(customer_id)
    return await action.update_profile(c, payload)


# --- Verification documents ---------------------------------------------------
@router.post("/me/documents", response_model=CustomerOut)
async def upload_document(
    file: UploadFile = File(...),
    customer_id: uuid.UUID = Depends(require_customer),
    customers: CustomerQuery = Depends(),
    action: CustomerAction = Depends(),
):
    c = await customers.current(customer_id)
    return await action.add_document(
        c,
        content_type=file.content_type,
        filename=file.filename,
        data=await file.read(),
    )


@router.delete("/me/documents/{idx}", response_model=CustomerOut)
async def delete_document(
    idx: int,
    customer_id: uuid.UUID = Depends(require_customer),
    customers: CustomerQuery = Depends(),
    action: CustomerAction = Depends(),
):
    c = await customers.current(customer_id)
    return await action.remove_document(c, idx)


# --- Orders (read-only; linked by phone) --------------------------------------
@router.get("/me/orders", response_model=list[OrderTrackOut])
async def my_orders(
    customer_id: uuid.UUID = Depends(require_customer),
    customers: CustomerQuery = Depends(),
):
    c = await customers.current(customer_id)
    return await customers.orders_for(c)


# --- Favorites ----------------------------------------------------------------
@router.get("/me/favorites", response_model=list[ProductOut])
async def my_favorites(
    customer_id: uuid.UUID = Depends(require_customer),
    favorites: FavoriteQuery = Depends(),
):
    return await favorites.products_for(customer_id)


@router.put("/me/favorites/{product_id}", status_code=204)
async def add_favorite(
    product_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    action: FavoriteAction = Depends(),
):
    await action.add(customer_id, product_id)


@router.delete("/me/favorites/{product_id}", status_code=204)
async def remove_favorite(
    product_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    action: FavoriteAction = Depends(),
):
    await action.remove(customer_id, product_id)


# --- Addresses ----------------------------------------------------------------
@router.get("/me/addresses", response_model=list[AddressOut])
async def list_addresses(
    customer_id: uuid.UUID = Depends(require_customer),
    addresses: AddressQuery = Depends(),
):
    return await addresses.list_for(customer_id)


@router.post("/me/addresses", response_model=AddressOut, status_code=201)
async def create_address(
    payload: AddressIn,
    customer_id: uuid.UUID = Depends(require_customer),
    action: AddressAction = Depends(),
):
    return await action.create(customer_id, payload)


@router.patch("/me/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    address_id: uuid.UUID,
    payload: AddressUpdate,
    customer_id: uuid.UUID = Depends(require_customer),
    addresses: AddressQuery = Depends(),
    action: AddressAction = Depends(),
):
    addr = await addresses.owned_or_404(address_id, customer_id)
    return await action.update(addr, payload)


@router.delete("/me/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    addresses: AddressQuery = Depends(),
    action: AddressAction = Depends(),
):
    addr = await addresses.owned_or_404(address_id, customer_id)
    await action.delete(addr)
