from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.domains.agents.models import AgentRetailer
from app.domains.customers import Customer
from app.shared.cqrs import BaseQuery


class AgentRetailerQuery(BaseQuery[AgentRetailer]):
    model = AgentRetailer

    async def assigned_customers(self, agent_id: UUID) -> list[Customer]:
        """All retailers (approved customers) assigned to this agent."""
        rows = await self.db.execute(
            select(Customer)
            .join(AgentRetailer, AgentRetailer.customer_id == Customer.id)
            .where(AgentRetailer.agent_id == agent_id)
            .order_by(Customer.created_at)
        )
        return list(rows.scalars().all())

    async def assigned_customer_or_404(
        self, agent_id: UUID, customer_id: UUID
    ) -> Customer:
        """The security boundary: an agent may only act on retailers assigned
        to them. Missing link and missing customer return the SAME 404."""
        link = await self.db.get(AgentRetailer, (agent_id, customer_id))
        if link is None:
            raise HTTPException(404, detail="Retailer not found")
        customer = await self.db.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(404, detail="Retailer not found")
        return customer
