"""Group→product resolution shared by the landing and portfolio read sides.

Moved verbatim from the old content service during the CQRS split. Lives in
queries/ because it is a pure read against the live catalog."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog import Product
from app.domains.content.schemas import LandingGroupOut


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
