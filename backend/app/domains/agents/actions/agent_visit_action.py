from uuid import UUID

from app.domains.agents.models import AgentVisit
from app.domains.agents.schemas import VisitCreate
from app.shared.cqrs import BaseAction


class AgentVisitAction(BaseAction[AgentVisit]):
    model = AgentVisit

    async def log(self, agent_id: UUID, payload: VisitCreate) -> AgentVisit:
        return await self.save(
            AgentVisit(
                agent_id=agent_id,
                customer_id=payload.customer_id,
                note=payload.note,
            )
        )
