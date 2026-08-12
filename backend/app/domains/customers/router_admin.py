import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.domains.customers.models import Customer, CustomerVerificationStatus
from app.domains.customers.schemas import CustomerAdminOut, VerificationUpdate
from app.services.sms import send_sms

router = APIRouter(dependencies=[Depends(require_admin)])

APPROVED_SMS = "احراز هویت شما با موفقیت انجام شد."


@router.get("/customers", response_model=list[CustomerAdminOut])
async def list_customers(
    status: str | None = None,
    page: int = Query(1, ge=1),
    # ponytail: generous default keeps the un-paginated admin UI working; wire
    # real pagination into the frontend before customer count nears the cap.
    page_size: int = Query(500, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(Customer).order_by(Customer.created_at.desc())
    if status:
        q = q.where(Customer.verification_status == status)
    q = q.offset((page - 1) * page_size).limit(page_size)
    return (await db.execute(q)).scalars().all()


@router.get("/customers/{customer_id}", response_model=CustomerAdminOut)
async def get_customer(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(404, detail="مشتری یافت نشد")
    return c


@router.patch("/customers/{customer_id}/verification", response_model=CustomerAdminOut)
async def set_verification(
    customer_id: uuid.UUID,
    payload: VerificationUpdate,
    db: AsyncSession = Depends(get_db),
):
    c = await db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(404, detail="مشتری یافت نشد")
    new = CustomerVerificationStatus(payload.status)
    if c.verification_status == new:
        return c
    c.verification_status = new
    if new == CustomerVerificationStatus.approved:
        c.verified_at = datetime.now(UTC)
        c.rejection_reason = None
        await send_sms(c.phone, APPROVED_SMS)
    else:  # rejected
        c.rejection_reason = payload.reason
        await send_sms(c.phone, f"مدارک شما تایید نشد. {payload.reason or ''}".strip())
    await db.commit()
    await db.refresh(c)
    return c
