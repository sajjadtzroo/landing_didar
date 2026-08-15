"""Admin customer management — thin HTTP layer over CustomerQuery /
VerifyCustomerAction."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.domains.customers.actions import VerifyCustomerAction
from app.domains.customers.queries import CustomerQuery
from app.domains.customers.schemas import CustomerAdminOut, VerificationUpdate
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/customers", response_model=list[CustomerAdminOut])
async def list_customers(
    status: str | None = None,
    page: int = Query(1, ge=1),
    # ponytail: generous default keeps the un-paginated admin UI working; wire
    # real pagination into the frontend before customer count nears the cap.
    page_size: int = Query(500, ge=1, le=500),
    customers: CustomerQuery = Depends(),
):
    return await customers.admin_list(status=status, page=page, page_size=page_size)


@router.get("/customers/{customer_id}", response_model=CustomerAdminOut)
async def get_customer(customer_id: uuid.UUID, customers: CustomerQuery = Depends()):
    return await customers.by_id_or_404(customer_id, detail="مشتری یافت نشد")


@router.patch("/customers/{customer_id}/verification", response_model=CustomerAdminOut)
async def set_verification(
    customer_id: uuid.UUID,
    payload: VerificationUpdate,
    customers: CustomerQuery = Depends(),
    action: VerifyCustomerAction = Depends(),
):
    c = await customers.by_id_or_404(customer_id, detail="مشتری یافت نشد")
    return await action.execute(c, payload)
