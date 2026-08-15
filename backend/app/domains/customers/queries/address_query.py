import uuid

from fastapi import HTTPException

from app.domains.customers.models import CustomerAddress
from app.shared.cqrs import BaseQuery


class AddressQuery(BaseQuery[CustomerAddress]):
    model = CustomerAddress

    async def list_for(self, customer_id: uuid.UUID) -> list[CustomerAddress]:
        return await self.all(
            self.stmt()
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.created_at)
        )

    async def owned_or_404(
        self, address_id: uuid.UUID, customer_id: uuid.UUID
    ) -> CustomerAddress:
        """Ownership is part of existence — someone else's address is a 404,
        never a 403 (don't leak that the id exists)."""
        addr = await self.by_id(address_id)
        if addr is None or addr.customer_id != customer_id:
            raise HTTPException(404, detail="Address not found")
        return addr
