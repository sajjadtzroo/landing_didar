import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.catalog import ProductOut

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class LandingGroupOut(BaseModel):
    """One product carousel on a landing — a named group of resolved products."""

    title: str
    eyebrow: str | None = None
    description: str | None = None
    products: list[ProductOut]


class LandingDetailOut(BaseModel):
    """Public payload for /landings/{slug} — meta + per-section content + the
    product groups with their products resolved from the catalog."""

    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    hero_video_url: str | None
    hero_poster_url: str | None
    content: dict
    groups: list[LandingGroupOut]


class LandingAdminOut(BaseModel):
    """Admin list/detail — the raw content blob (groups hold product ids)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    title: str
    hero_video_url: str | None
    hero_poster_url: str | None
    content: dict | None


class LandingCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)

    @field_validator("slug")
    @classmethod
    def _slug_ok(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError("slug must be lowercase letters/numbers/hyphens")
        return v


class LandingUpdate(BaseModel):
    # slug is immutable (route + redirect depend on it) — not editable.
    title: str | None = Field(default=None, min_length=1, max_length=120)
    hero_video_url: str | None = None
    hero_poster_url: str | None = None
    content: dict | None = None
