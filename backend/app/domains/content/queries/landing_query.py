from sqlalchemy import select

from app.domains.content.models import Landing
from app.domains.content.queries.product_groups import resolve_groups
from app.domains.content.schemas import LandingGroupOut
from app.shared.cqrs import BaseQuery


class LandingQuery(BaseQuery[Landing]):
    model = Landing

    async def by_slug(self, slug: str) -> Landing | None:
        return await self.one_or_none(self.stmt().where(Landing.slug == slug))

    async def list_admin(self) -> list[Landing]:
        return await self.all(self.stmt().order_by(Landing.slug))

    async def slug_taken(self, slug: str) -> bool:
        return bool(
            await self.db.scalar(select(Landing.id).where(Landing.slug == slug))
        )

    async def resolve_groups(self, raw_groups: list[dict]) -> list[LandingGroupOut]:
        """A landing's content groups with products resolved from the catalog."""
        return await resolve_groups(self.db, raw_groups)
