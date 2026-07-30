import uuid

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    weight_grams: Mapped[float | None] = mapped_column(Numeric(8, 2))
    karat: Mapped[int | None] = mapped_column(Integer)
    # NULL price => "price on request" (gold rate moves daily)
    price: Mapped[float | None] = mapped_column(Numeric(12, 0))
    # اجرت — making-fee percentage (the customer-facing figure; price is admin-only)
    ojrat_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    image_url: Mapped[str | None] = mapped_column(String(500))
    # "daily" | "luxury" — groups products into the two landing carousels
    category: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
