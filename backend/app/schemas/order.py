import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.provinces import IRAN_PROVINCES
from app.models.order import ContactMethod, OrderStatus

# Mirror of the client Zod rules — server is the source of truth.
PHONE_RE = r"^09\d{9}$"


class OrderItemIn(BaseModel):
    product_id: uuid.UUID | None = None
    quantity: int = Field(ge=1, le=999)


class OrderCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=60)
    phone: str = Field(pattern=PHONE_RE)
    store_name: str = Field(min_length=2, max_length=80)
    province: str
    city: str | None = Field(default=None, max_length=60)
    contact_method: ContactMethod = ContactMethod.call
    note: str | None = Field(default=None, max_length=300)
    items: list[OrderItemIn] = Field(min_length=1)

    # Attribution (optional, captured client-side)
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    referrer: str | None = None

    # Honeypot — must stay empty (real users never see it)
    website: str | None = None

    @field_validator("province")
    @classmethod
    def province_in_list(cls, v: str) -> str:
        if v not in IRAN_PROVINCES:
            raise ValueError("province must be one of the Iran province list")
        return v


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID | None
    product_name: str
    unit_weight_grams: Decimal | None
    unit_price: Decimal | None  # legacy, no longer populated
    quantity: int


class OrderStatusLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    from_status: OrderStatus | None
    to_status: OrderStatus
    created_at: datetime


class OrderCreatedOut(BaseModel):
    reference: str
    total: Decimal


class OrderTrackOut(BaseModel):
    """Public order-status view (reference + phone lookup). Deliberately omits
    stored PII (name/address) — the customer already has it; the response only
    confirms status + line items + the status timeline."""

    model_config = ConfigDict(from_attributes=True)
    reference: str
    status: OrderStatus
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]
    status_log: list[OrderStatusLogOut]
    serial_codes: list[str] = []  # authenticity codes once delivered


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reference: str
    full_name: str
    phone: str
    store_name: str
    province: str
    city: str | None
    contact_method: ContactMethod
    note: str | None
    internal_note: str | None
    status: OrderStatus
    total: Decimal
    is_read: bool
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    referrer: str | None
    created_at: datetime


class OrderDetailOut(OrderOut):
    items: list[OrderItemOut]
    status_log: list[OrderStatusLogOut]
    serial_codes: list[str] = []  # authenticity codes minted on delivery


class OrderListOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int
    unread: int


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    internal_note: str | None = Field(default=None, max_length=1000)
    is_read: bool | None = None
