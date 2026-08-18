import uuid

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "category IN ('daily', 'lux_daily', 'luxury', 'watch')",
            name="ck_products_category",
        ),
        CheckConstraint(
            "product_status IN ('sellable', 'sample', 'not_for_sale')",
            name="ck_products_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    weight_grams: Mapped[float | None] = mapped_column(Numeric(8, 2))
    # Free-text weight shown to customers when a piece/set has a RANGE ("۱۲-۱۵
    # گرم") the single numeric can't express. weight_grams stays for sort/filter.
    weight_display: Mapped[str | None] = mapped_column(String(40))
    karat: Mapped[int | None] = mapped_column(Integer)
    # NULL price => "price on request" (gold rate moves daily)
    price: Mapped[float | None] = mapped_column(Numeric(12, 0))
    # اجرت — making-fee percentage (the customer-facing figure; price is admin-only)
    ojrat_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    image_url: Mapped[str | None] = mapped_column(String(500))
    # Gallery: served media paths imported from MinIO (folder {sku}/). image_url
    # stays the primary/thumbnail (= images[0] after an import).
    images: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]", default=list
    )
    # "daily" | "luxury" — groups products into the two landing carousels
    category: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    # Supplier / maker (admin-only; not exposed on the public product payload).
    supplier: Mapped[str | None] = mapped_column(String(120))
    # Sellability, orthogonal to `is_active` visibility: sellable (normal),
    # sample (نمونه — shown but not orderable), not_for_sale (hidden from shop).
    product_status: Mapped[str] = mapped_column(
        String(16), default="sellable", server_default="sellable", nullable=False
    )
    # Whether this product carries a warranty (consumed by the Warranty module).
    warrantable: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Curated into the "پرفروش‌ترین‌ها" carousel. When any product is featured the
    # section shows the curated set; otherwise it falls back to real sales data.
    is_featured: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
