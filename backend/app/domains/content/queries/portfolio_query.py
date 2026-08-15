from sqlalchemy import select

from app.domains.content.models import Portfolio
from app.domains.content.queries.product_groups import resolve_groups
from app.domains.content.schemas import LandingGroupOut
from app.shared.cqrs import BaseQuery


class PortfolioQuery(BaseQuery[Portfolio]):
    model = Portfolio

    async def list_public(self) -> list[Portfolio]:
        """Active portfolios (curated /shop sections), ordered."""
        return await self.all(
            self.stmt().where(Portfolio.is_active).order_by(Portfolio.sort_order)
        )

    async def by_slug_public(self, slug: str) -> Portfolio | None:
        """Active-only lookup — inactive portfolios 404 (matching the list)."""
        return await self.one_or_none(
            self.stmt().where(Portfolio.slug == slug, Portfolio.is_active)
        )

    async def list_admin(self) -> list[Portfolio]:
        return await self.all(self.stmt().order_by(Portfolio.sort_order))

    async def slug_taken(self, slug: str) -> bool:
        return bool(
            await self.db.scalar(select(Portfolio.id).where(Portfolio.slug == slug))
        )

    async def resolve_groups(self, raw_groups: list[dict]) -> list[LandingGroupOut]:
        """A portfolio's content groups with products resolved from the catalog."""
        return await resolve_groups(self.db, raw_groups)
