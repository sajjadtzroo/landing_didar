from app.domains.agents.schemas import AgentOrderCreate
from app.domains.customers import Customer
from app.domains.orders import (
    CreateOrderAction,
    DeliveryProof,
    Order,
    OrderAction,
    OrderCreate,
    OrderStatus,
)
from app.domains.serials import service as serial_service
from app.domains.users import User
from app.shared.cqrs import BaseAction


class AgentOrderAction(BaseAction[Order]):
    model = Order

    async def place_for_retailer(
        self, agent: User, customer: Customer, payload: AgentOrderCreate
    ) -> Order:
        """Order on behalf of an assigned retailer. Identity comes from the
        retailer's profile (server-side), items/province from the agent's form.
        Attribution (agent_id) is stamped in a second commit — the order is
        already safely persisted by CreateOrderAction."""
        create = OrderCreate(
            full_name=(
                customer.full_name or customer.store_name or "خرده‌فروش دیدار"
            )[:60],
            phone=customer.phone,
            store_name=(customer.store_name or customer.full_name or "فروشگاه")[:80],
            province=payload.province,
            city=payload.city,
            contact_method="agent",
            note=payload.note,
            items=payload.items,
        )
        order = await CreateOrderAction(self.db).execute(
            create, idempotency_key=None, ip=None
        )
        order.agent_id = agent.id
        return await self.commit_and_refresh(order)

    async def deliver(self, order: Order, agent: User, proof: DeliveryProof) -> Order:
        """Mark the agent's order delivered with proof — mints authenticity
        serials exactly like the admin path. change_status does not commit;
        this command owns the one transaction."""
        await OrderAction(self.db).change_status(order, OrderStatus.delivered)
        await serial_service.generate_for_order(self.db, order)
        order.delivery_assignee = agent.full_name or agent.username
        order.delivery_proof = proof.model_dump(exclude_none=True)
        return await self.commit_and_refresh(order)
