import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.warranty import BuybackStatus
from app.schemas.order import PHONE_RE


class WarrantyActivate(BaseModel):
    full_name: str = Field(min_length=3, max_length=60)
    phone: str = Field(pattern=PHONE_RE)


class WarrantyOut(BaseModel):
    """Public warranty state on the passport — no PII."""

    started_at: datetime
    expires_at: datetime
    active: bool


class BuybackCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=60)
    phone: str = Field(pattern=PHONE_RE)
    note: str | None = Field(default=None, max_length=300)


class BuybackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    serial_id: uuid.UUID
    code: str  # display form, joined in
    product_name: str
    requester_name: str
    requester_phone: str
    note: str | None
    status: BuybackStatus
    offered_price: Decimal | None
    admin_note: str | None
    created_at: datetime


class BuybackListOut(BaseModel):
    items: list[BuybackOut]
    total: int
    page: int
    page_size: int


class BuybackUpdate(BaseModel):
    status: BuybackStatus | None = None
    offered_price: Decimal | None = Field(default=None, ge=0)
    admin_note: str | None = Field(default=None, max_length=300)
