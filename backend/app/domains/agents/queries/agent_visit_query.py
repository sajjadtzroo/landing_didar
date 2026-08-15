from uuid import UUID

from app.domains.agents.models import AgentVisit
from app.shared.cqrs import BaseQuery


class AgentVisitQuery(BaseQuery[AgentVisit]):
    model = AgentVisit

    async def for_agent(
        self,
        agent_id: UUID,
        customer_id: UUID | None = None,
        limit: int = 100,
    ) -> list[AgentVisit]:
        stmt = self.stmt().where(AgentVisit.agent_id == agent_id)
        if customer_id:
            stmt = stmt.where(AgentVisit.customer_id == customer_id)
        return await self.all(
            stmt.order_by(AgentVisit.created_at.desc()).limit(limit)
        )
