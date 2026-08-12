import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.orders import OrderStatus
from app.domains.orders import OrderItemIn


class AgentRetailerOut(BaseModel):
    """A retailer (approved customer) as the agent sees them."""

    id: uuid.UUID
    store_name: str | None
    full_name: str | None
    phone: str
    province: str | None  # from the default address, if any
    city: str | None


class AgentOrderCreate(BaseModel):
    customer_id: uuid.UUID
    province: str
    city: str | None = Field(default=None, max_length=60)
    note: str | None = Field(default=None, max_length=300)
    items: list[OrderItemIn] = Field(min_length=1)


class AgentOrderOut(BaseModel):
    """The agent's view of an order — NO admin-only fields (internal_note,
    is_read, attribution)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reference: str
    full_name: str
    store_name: str
    province: str
    city: str | None
    note: str | None
    status: OrderStatus
    total: Decimal
    created_at: datetime
    agent_username: str | None = None


class AgentOrderDetailOut(AgentOrderOut):
    serial_codes: list[str] = []
    delivered_at: datetime | None = None


# --- گالری سیار (WO 7.6) ---
GalleryKind = Literal["sample", "sellable"]


class GalleryItemOut(BaseModel):
    id: uuid.UUID
    code: str  # display form
    product_name: str
    image_url: str | None
    kind: GalleryKind
    status: str  # with_agent | returned | sold
    note: str | None
    created_at: datetime


class GalleryOut(BaseModel):
    items: list[GalleryItemOut]
    # {"with_agent": n, "sample": n, "sellable": n, "sold": n, "returned": n}
    counts: dict[str, int]


class GalleryAssignIn(BaseModel):
    agent_id: uuid.UUID
    code: str = Field(min_length=4, max_length=16)
    kind: GalleryKind | None = None  # default: derived from the product
    note: str | None = Field(default=None, max_length=300)


class GallerySellIn(BaseModel):
    note: str | None = Field(default=None, max_length=300)  # buyer / context


class VisitCreate(BaseModel):
    customer_id: uuid.UUID
    note: str = Field(min_length=2, max_length=500)


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    note: str
    created_at: datetime
