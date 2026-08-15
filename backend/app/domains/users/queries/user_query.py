import uuid

from sqlalchemy import select

from app.domains.users.models import User
from app.shared.cqrs import BaseQuery

# agents' public API itself imports users (allowed by the DAG — users is the
# bottom layer), so importing agents at module scope here would make
# users.__init__ circular — the retailer lookup below imports lazily instead.


class UserQuery(BaseQuery[User]):
    model = User

    async def list_all(self) -> list[User]:
        return await self.all(self.stmt().order_by(User.created_at))

    async def active_by_username(self, username: str) -> User | None:
        return await self.one_or_none(
            self.stmt().where(User.username == username, User.is_active)
        )

    async def retailer_ids(self, agent_id: uuid.UUID) -> list[uuid.UUID]:
        """Customer ids assigned to this agent (WO 7.5 assignment)."""
        from app.domains.agents import AgentRetailer  # lazy — see module comment

        rows = await self.db.execute(
            select(AgentRetailer.customer_id).where(AgentRetailer.agent_id == agent_id)
        )
        return list(rows.scalars().all())
