from uuid import UUID

from fastapi import HTTPException

from app.domains.orders import Order
from app.domains.users import AdminRole, User
from app.shared.cqrs import BaseQuery


class AgentOrderQuery(BaseQuery[Order]):
    """Reads over orders placed BY agents — scoped to the logged-in agent."""

    model = Order

    async def for_agent(self, agent_id: UUID, limit: int = 100) -> list[Order]:
        return await self.all(
            self.stmt()
            .where(Order.agent_id == agent_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )

    async def owned_or_404(self, order_id: UUID, agent: User) -> Order:
        """An agent only sees their own orders; a superadmin sees all
        (oversight path). Someone else's order 404s — never a 403 that
        would confirm the order exists."""
        order = await self.by_id(order_id)
        is_super = agent.role == AdminRole.superadmin  # oversight path
        if order is None or (not is_super and order.agent_id != agent.id):
            raise HTTPException(404, detail="Order not found")
        return order
