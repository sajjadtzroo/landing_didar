from fastapi import HTTPException

from app.core.content_defaults import default_content
from app.domains.content.models import Landing
from app.domains.content.queries import LandingQuery
from app.domains.content.schemas import LandingCreate, LandingUpdate
from app.domains.content.services import bust_landing_cache
from app.shared.cqrs import BaseAction


class LandingAction(BaseAction[Landing]):
    model = Landing

    async def create(self, payload: LandingCreate) -> Landing:
        if await LandingQuery(self.db).slug_taken(payload.slug):
            raise HTTPException(409, detail="A landing with this slug already exists")
        return await self.save(
            Landing(slug=payload.slug, title=payload.title, content=default_content())
        )

    async def update(self, landing: Landing, payload: LandingUpdate) -> Landing:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(landing, k, v)
        landing = await self.commit_and_refresh(landing)
        # Bust AFTER commit so the public read re-caches the fresh content.
        await bust_landing_cache(landing.slug)
        return landing

    async def delete(self, landing: Landing) -> None:
        slug = landing.slug
        await super().delete(landing)
        await bust_landing_cache(slug)
