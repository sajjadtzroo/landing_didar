import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.landing import LandingGroupOut

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(v: str) -> str:
    v = v.strip().lower()
    if not _SLUG_RE.match(v):
        raise ValueError("slug must be lowercase letters/numbers/hyphens")
    return v


class PortfolioAdminOut(BaseModel):
    """Admin list/detail — the raw content blob (groups hold product ids)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    cover_image_url: str | None
    is_active: bool
    sort_order: int
    content: dict | None


class PortfolioPublicOut(BaseModel):
    """Public payload for /portfolios — one curated section with its products
    resolved from the catalog. Reuses the landing group shape."""

    id: uuid.UUID
    name: str
    slug: str
    cover_image_url: str | None
    groups: list[LandingGroupOut]


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=80)

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: str) -> str:
        return _validate_slug(v)


class PortfolioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    cover_image_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    content: dict | None = None

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: str | None) -> str | None:
        return _validate_slug(v) if v is not None else v
