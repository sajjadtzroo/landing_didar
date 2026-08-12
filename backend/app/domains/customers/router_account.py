"""Customer account panel: phone-OTP login + orders, favorites, addresses, profile.

Session is a signed cookie (didar_customer), mirroring the admin auth scheme with
a different salt. Orders are linked to a customer by matching phone, so purchases
made before signup still show up.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.limiter import limiter
from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    CUSTOMER_COOKIE,
    hash_otp_async,
    issue_customer_session,
    verify_otp_async,
)
from app.domains.catalog import ProductOut
from app.domains.customers.dependencies import require_customer
from app.domains.customers.models import (
    Customer,
    CustomerAddress,
    CustomerVerificationStatus,
    Favorite,
    OtpCode,
)
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
from app.domains.orders import Order, OrderTrackOut
from app.models import Product
from app.services.storage import get_storage
from app.shared.sms import send_sms

router = APIRouter()

OTP_TTL = 300  # seconds a code stays valid
OTP_MAX_ATTEMPTS = 5  # wrong tries before a code is dead

_ALLOWED_DOC = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_DOCS = 5


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
    request: Request, payload: OtpRequestIn, db: AsyncSession = Depends(get_db)
):
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        OtpCode(
            phone=payload.phone,
            code_hash=await hash_otp_async(code),
            expires_at=datetime.now(UTC) + timedelta(seconds=OTP_TTL),
        )
    )
    await db.commit()
    # Allowlisted test phones skip the real gateway and get the code back directly
    # (QA / app-review logins in prod). Everyone else gets a real SMS.
    is_test = payload.phone in settings.otp_test_phone_set
    if not is_test:
        await send_sms(payload.phone, f"کد ورود دیدار: {code}")
    # dev_code outside production, or for test phones even in production.
    reveal = is_test or not settings.cookie_secure
    return OtpRequestOut(sent=True, dev_code=code if reveal else None)


@router.post("/otp/verify", response_model=CustomerOut)
async def verify_otp_code(
    payload: OtpVerifyIn, response: Response, db: AsyncSession = Depends(get_db)
):
    otp = (
        (
            await db.execute(
                select(OtpCode)
                .where(OtpCode.phone == payload.phone, OtpCode.consumed.is_(False))
                .order_by(OtpCode.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    now = datetime.now(UTC)
    invalid = HTTPException(400, detail="کد نامعتبر یا منقضی شده است")
    if otp is None or otp.expires_at < now or otp.attempts >= OTP_MAX_ATTEMPTS:
        raise invalid
    if not await verify_otp_async(payload.code, otp.code_hash):
        otp.attempts += 1
        await db.commit()
        raise invalid
    otp.consumed = True
    customer = (
        await db.execute(select(Customer).where(Customer.phone == payload.phone))
    ).scalar_one_or_none()
    if customer is None:
        customer = Customer(phone=payload.phone)
        db.add(customer)
    await db.commit()
    await db.refresh(customer)
    _set_customer_cookie(response, issue_customer_session(str(customer.id)))
    return customer


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(CUSTOMER_COOKIE, path="/")
    return {"detail": "ok"}


async def _current(db: AsyncSession, customer_id: uuid.UUID) -> Customer:
    c = await db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(401, detail="Not authenticated")
    return c


@router.get("/me", response_model=CustomerOut)
async def me(
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    return await _current(db, customer_id)


@router.patch("/me", response_model=CustomerOut)
async def update_me(
    payload: CustomerUpdate,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    c = await _current(db, customer_id)
    c.full_name = payload.full_name
    c.store_name = payload.store_name
    await db.commit()
    await db.refresh(c)
    return c


# --- Verification documents ---------------------------------------------------
@router.post("/me/documents", response_model=CustomerOut)
async def upload_document(
    file: UploadFile = File(...),
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in _ALLOWED_DOC:
        raise HTTPException(415, detail="فرمت فایل پشتیبانی نمی‌شود")
    c = await _current(db, customer_id)
    if len(c.verification_documents) >= _MAX_DOCS:
        raise HTTPException(400, detail="حداکثر تعداد مدارک بارگذاری شده است")
    data = await file.read()
    from app.services.storage import sniff_ok

    if not sniff_ok(file.content_type, data):
        raise HTTPException(415, detail="محتوای فایل با نوع آن هم‌خوانی ندارد")
    if len(data) > _MAX_DOC_BYTES:
        raise HTTPException(413, detail="حجم فایل زیاد است (حداکثر ۱۰ مگابایت)")
    url = await get_storage().save(file.filename or "document", data)
    # reassign (not append) so SQLAlchemy flags the JSONB change
    c.verification_documents = [
        *c.verification_documents,
        {
            "url": url,
            "filename": file.filename,
            "uploaded_at": datetime.now(UTC).isoformat(),
        },
    ]
    if c.verification_status in (
        CustomerVerificationStatus.unverified,
        CustomerVerificationStatus.rejected,
    ):
        c.verification_status = CustomerVerificationStatus.pending
        c.rejection_reason = None
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/me/documents/{idx}", response_model=CustomerOut)
async def delete_document(
    idx: int,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    c = await _current(db, customer_id)
    if c.verification_status != CustomerVerificationStatus.pending:
        raise HTTPException(400, detail="فقط در وضعیت در انتظار بررسی قابل حذف است")
    if idx < 0 or idx >= len(c.verification_documents):
        raise HTTPException(404, detail="مدرک یافت نشد")
    docs = list(c.verification_documents)
    docs.pop(idx)
    c.verification_documents = docs
    await db.commit()
    await db.refresh(c)
    return c


# --- Orders (read-only; linked by phone) --------------------------------------
@router.get("/me/orders", response_model=list[OrderTrackOut])
async def my_orders(
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    c = await _current(db, customer_id)
    return (
        (
            await db.execute(
                select(Order)
                .where(Order.phone == c.phone)
                .order_by(Order.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


# --- Favorites ----------------------------------------------------------------
@router.get("/me/favorites", response_model=list[ProductOut])
async def my_favorites(
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    return (
        (
            await db.execute(
                select(Product)
                .join(Favorite, Favorite.product_id == Product.id)
                .where(Favorite.customer_id == customer_id)
                .order_by(Favorite.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@router.put("/me/favorites/{product_id}", status_code=204)
async def add_favorite(
    product_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    if await db.get(Product, product_id) is None:
        raise HTTPException(404, detail="Product not found")
    exists = await db.get(
        Favorite, {"customer_id": customer_id, "product_id": product_id}
    )
    if exists is None:
        db.add(Favorite(customer_id=customer_id, product_id=product_id))
        await db.commit()


@router.delete("/me/favorites/{product_id}", status_code=204)
async def remove_favorite(
    product_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(Favorite).where(
            Favorite.customer_id == customer_id, Favorite.product_id == product_id
        )
    )
    await db.commit()


# --- Addresses ----------------------------------------------------------------
async def _clear_default(db: AsyncSession, customer_id: uuid.UUID) -> None:
    await db.execute(
        update(CustomerAddress)
        .where(CustomerAddress.customer_id == customer_id)
        .values(is_default=False)
    )


@router.get("/me/addresses", response_model=list[AddressOut])
async def list_addresses(
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    return (
        (
            await db.execute(
                select(CustomerAddress)
                .where(CustomerAddress.customer_id == customer_id)
                .order_by(CustomerAddress.created_at)
            )
        )
        .scalars()
        .all()
    )


@router.post("/me/addresses", response_model=AddressOut, status_code=201)
async def create_address(
    payload: AddressIn,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    if payload.is_default:
        await _clear_default(db, customer_id)
    addr = CustomerAddress(customer_id=customer_id, **payload.model_dump())
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.patch("/me/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    address_id: uuid.UUID,
    payload: AddressUpdate,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    addr = await db.get(CustomerAddress, address_id)
    if addr is None or addr.customer_id != customer_id:
        raise HTTPException(404, detail="Address not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default"):
        await _clear_default(db, customer_id)
    for k, v in data.items():
        setattr(addr, k, v)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.delete("/me/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    addr = await db.get(CustomerAddress, address_id)
    if addr is None or addr.customer_id != customer_id:
        raise HTTPException(404, detail="Address not found")
    await db.delete(addr)
    await db.commit()
