import uuid

from sqlalchemy import update

from app.domains.customers.models import CustomerAddress
from app.domains.customers.schemas import AddressIn, AddressUpdate
from app.shared.cqrs import BaseAction


class AddressAction(BaseAction[CustomerAddress]):
    model = CustomerAddress

    async def _clear_default(self, customer_id: uuid.UUID) -> None:
        """At most one default address — unset the flag everywhere first."""
        await self.db.execute(
            update(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .values(is_default=False)
        )

    async def create(
        self, customer_id: uuid.UUID, payload: AddressIn
    ) -> CustomerAddress:
        if payload.is_default:
            await self._clear_default(customer_id)
        return await self.save(
            CustomerAddress(customer_id=customer_id, **payload.model_dump())
        )

    async def update(
        self, addr: CustomerAddress, payload: AddressUpdate
    ) -> CustomerAddress:
        data = payload.model_dump(exclude_unset=True)
        if data.get("is_default"):
            await self._clear_default(addr.customer_id)
        for k, v in data.items():
            setattr(addr, k, v)
        return await self.commit_and_refresh(addr)
