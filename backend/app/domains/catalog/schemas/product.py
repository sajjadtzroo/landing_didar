import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["daily", "lux_daily", "luxury"]
# Sellability, orthogonal to is_active: sellable (normal), sample (نمونه — shown
# but not orderable), not_for_sale (غیرقابل‌فروش — hidden from the public shop).
ProductStatus = Literal["sellable", "sample", "not_for_sale"]


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    sku: str = Field(min_length=1, max_length=40)
    description: str | None = None
    weight_grams: Decimal | None = None
    weight_display: str | None = Field(default=None, max_length=40)
    karat: int | None = Field(default=None, ge=1, le=24)
    price: Decimal | None = None  # None => price on request
    # اجرت (making-fee %)
    ojrat_percent: Decimal | None = Field(default=None, ge=0, le=100)
    image_url: str | None = None
    category: Category = "daily"
    # Public-safe: the frontend needs these to gate ordering (sample) + warranty.
    product_status: ProductStatus = "sellable"
    warrantable: bool = True
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0


class ProductCreate(ProductBase):
    supplier: str | None = Field(default=None, max_length=120)  # admin-only


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    sku: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = None
    weight_grams: Decimal | None = None
    weight_display: str | None = Field(default=None, max_length=40)
    karat: int | None = Field(default=None, ge=1, le=24)
    price: Decimal | None = None
    ojrat_percent: Decimal | None = Field(default=None, ge=0, le=100)
    image_url: str | None = None
    category: Category | None = None
    supplier: str | None = Field(default=None, max_length=120)
    product_status: ProductStatus | None = None
    warrantable: bool | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    images: list[str] = []  # gallery paths imported from MinIO; [] until imported


class AdminProductOut(ProductOut):
    """Admin view — adds the internal supplier/maker field."""

    supplier: str | None = None
