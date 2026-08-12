import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Landing(Base):
    """A landing page. Admin can create/delete them; slug is fixed per landing
    (the public route /l/<slug> and the `/` redirect depend on it). Every section's
    content (hero text, trust cards, product groups, faq, footer, promo, section
    toggles) lives per-landing in `content` (JSONB) — see core.content_defaults for
    its shape and defaults. Hero *media* keeps its own columns (used by SEO/preload)."""

    __tablename__ = "landings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    hero_video_url: Mapped[str | None] = mapped_column(String(500))
    hero_poster_url: Mapped[str | None] = mapped_column(String(500))
    # Per-section content; see core.content_defaults.default_content() for shape.
    content: Mapped[dict | None] = mapped_column(JSONB)
