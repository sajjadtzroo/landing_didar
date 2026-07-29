import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductOut


class LandingDetailOut(BaseModel):
    """Public payload for /landings/{slug} — meta + ordered active products."""

    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    hero_video_url: str | None
    hero_poster_url: str | None
    products: list[ProductOut]


class LandingAdminOut(BaseModel):
    """Admin list/detail — includes the assigned product ids in display order."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    title: str
    hero_video_url: str | None
    hero_poster_url: str | None
    product_ids: list[uuid.UUID]


class LandingUpdate(BaseModel):
    # slug is immutable (route + redirect depend on it) — not editable.
    title: str | None = Field(default=None, min_length=1, max_length=120)
    hero_video_url: str | None = None
    hero_poster_url: str | None = None


class LandingProductsSet(BaseModel):
    product_ids: list[uuid.UUID]
