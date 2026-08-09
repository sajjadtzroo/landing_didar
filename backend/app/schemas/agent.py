import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import OrderItemIn


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


class VisitCreate(BaseModel):
    customer_id: uuid.UUID
    note: str = Field(min_length=2, max_length=500)


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    note: str
    created_at: datetime
