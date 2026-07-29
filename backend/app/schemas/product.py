import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    sku: str = Field(min_length=1, max_length=40)
    description: str | None = None
    weight_grams: Decimal | None = None
    karat: int | None = Field(default=None, ge=1, le=24)
    price: Decimal | None = None  # None => price on request
    image_url: str | None = None
    is_active: bool = True
    sort_order: int = 0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    sku: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = None
    weight_grams: Decimal | None = None
    karat: int | None = Field(default=None, ge=1, le=24)
    price: Decimal | None = None
    image_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
