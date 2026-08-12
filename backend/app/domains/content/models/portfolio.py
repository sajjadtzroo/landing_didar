import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Portfolio(Base):
    """An admin-curated, named collection of products shown as a section on /shop.

    Shares the landing product-group shape: `content = {"groups": [{title, eyebrow,
    description, product_ids[]}, ...]}`. Kept as its own table (not a landing) so it
    stays independent of the landing/route machinery. `sort_order` orders portfolios
    on /shop; `is_active` hides one without deleting it."""

    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # {"groups": [{title, eyebrow, description, product_ids[]}, ...]}
    content: Mapped[dict | None] = mapped_column(JSONB)
