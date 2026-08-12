"""Content-domain helpers: public-cache busting + group→product resolution.

Moved verbatim from app/api/v1/public.py during the domain migration."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete
from app.domains.content.schemas import LandingGroupOut
from app.models.product import Product


async def bust_landing_cache(slug: str) -> None:
    """Drop a landing's cached payload so an admin edit shows immediately instead
    of after the TTL. Called by the admin landings router on mutate."""
    await cache_delete(f"cache:landing:{slug}")


async def bust_portfolios_cache() -> None:
    """Drop the cached /portfolios payload so an admin edit shows immediately.
    Called by the admin portfolios router on mutate."""
    await cache_delete("cache:portfolios")


async def bust_portfolio_cache(slug: str) -> None:
    """Drop a single portfolio's cached detail payload. Called by the admin
    portfolios router on mutate (alongside bust_portfolios_cache for the list)."""
    await cache_delete(f"cache:portfolio:{slug}")


def _as_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def resolve_groups(
    db: AsyncSession, raw_groups: list[dict]
) -> list[LandingGroupOut]:
    """Resolve each group's `product_ids` against the live catalog in one query.
    A product is dropped if it's missing or inactive (ids live in JSON, so there's
    no FK/CASCADE — we filter here). Shared by landings and portfolios."""
    wanted = {
        u
        for g in raw_groups
        for pid in (g.get("product_ids") or [])
        if (u := _as_uuid(pid)) is not None
    }
    by_id: dict[uuid.UUID, Product] = {}
    if wanted:
        rows = (
            await db.execute(
                select(Product).where(
                    Product.id.in_(wanted),
                    Product.is_active,
                    Product.product_status != "not_for_sale",
                )
            )
        ).scalars().all()
        by_id = {p.id: p for p in rows}

    groups: list[LandingGroupOut] = []
    for g in raw_groups:
        items = [
            by_id[_as_uuid(pid)]
            for pid in (g.get("product_ids") or [])
            if _as_uuid(pid) in by_id
        ]
        groups.append(
            LandingGroupOut(
                title=g.get("title") or "",
                eyebrow=g.get("eyebrow"),
                description=g.get("description"),
                products=list(items),
            )
        )
    return groups
