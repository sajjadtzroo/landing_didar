import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.serials.serial_models import ProductSerialStatus


class SerialGenerate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=5000)


class SerialUpdate(BaseModel):
    status: ProductSerialStatus | None = None
    note: str | None = Field(default=None, max_length=300)


class SerialOut(BaseModel):
    """Admin view. `code` is the display form; verify_count/first_verified_at come
    from the scan log (the copy-attack signal)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str  # display form (DGV-XXXXXXXX)
    product_id: uuid.UUID
    product_name: str
    karat: int | None
    weight_grams: Decimal | None
    status: ProductSerialStatus
    batch_id: uuid.UUID
    note: str | None
    created_at: datetime
    order_reference: str | None = None  # set when minted for a delivered order
    verify_count: int = 0
    first_verified_at: datetime | None = None


class SerialListOut(BaseModel):
    items: list[SerialOut]
    total: int
    page: int
    page_size: int


class WarrantyState(BaseModel):
    started_at: datetime
    expires_at: datetime
    active: bool


class SerialEventOut(BaseModel):
    """One passport-timeline entry. `minted` is derived from created_at; stored
    types are sold/revoked/restored (+ warranty/buyback in later phases)."""

    type: str
    at: datetime


class SerialVerifyOut(BaseModel):
    """Public authenticity certificate — reads the SNAPSHOT (no live join, no PII,
    no internal status). `issued_at` is the code's generation date, not a sale date.
    `events` is the passport timeline (issue + sale)."""

    code: str  # display form
    product_name: str
    karat: int | None
    weight_grams: Decimal | None
    image_url: str | None
    issued_at: datetime
    events: list[SerialEventOut] = []
    # Warranty state (WO 7.8) — status only, no PII. `warranty_available` means
    # the piece is sold + warrantable + not yet activated.
    warranty: WarrantyState | None = None
    warranty_available: bool = False
    # Latest buyback request status, if any (WO 7.9) — no price, no PII.
    buyback_status: str | None = None
