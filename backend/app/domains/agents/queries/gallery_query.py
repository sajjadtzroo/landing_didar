from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.domains.agents.models import MobileGalleryItem
from app.domains.users import AdminRole, User
from app.shared.cqrs import BaseQuery


class GalleryQuery(BaseQuery[MobileGalleryItem]):
    model = MobileGalleryItem

    async def for_agent(self, agent_id: UUID) -> list[MobileGalleryItem]:
        """Everything ever handed to this agent, newest first — callers split
        active ("with_agent") from history (sold / returned)."""
        return await self.all(
            self.stmt()
            .where(MobileGalleryItem.agent_id == agent_id)
            .order_by(MobileGalleryItem.created_at.desc())
        )

    async def owned_or_404(
        self, item_id: UUID, agent_id: UUID
    ) -> MobileGalleryItem:
        """An agent only touches items in their own bag; someone else's item
        404s the same way as a missing one."""
        item = await self.by_id(item_id)
        if item is None or item.agent_id != agent_id:
            raise HTTPException(404, detail="Item not found")
        return item

    async def active_agents(self) -> list[User]:
        """Active agent accounts for the admin gallery picker (admin-level;
        /admin/users is superadmin-only by design)."""
        rows = await self.db.execute(
            select(User)
            .where(User.role == AdminRole.agent, User.is_active)
            .order_by(User.created_at)
        )
        return list(rows.scalars().all())
