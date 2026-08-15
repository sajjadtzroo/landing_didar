import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import noload

from app.domains.customers.models import Customer
from app.shared.cqrs import BaseQuery


class CustomerQuery(BaseQuery[Customer]):
    model = Customer

    async def current(self, customer_id: uuid.UUID) -> Customer:
        """Session customer or 401 — a signed cookie may outlive its row."""
        c = await self.by_id(customer_id)
        if c is None:
            raise HTTPException(401, detail="Not authenticated")
        return c

    async def admin_list(
        self, *, status: str | None, page: int, page_size: int
    ) -> list[Customer]:
        """Newest-first admin listing, optionally filtered by verification
        status. Pages manually (no MAX_PAGE_SIZE cap): the un-paginated admin
        UI relies on the generous 500 default until real pagination lands."""
        # The admin row schema uses neither relationship — without noload the
        # model-level lazy="selectin" hydrates addresses+favorites for all 500.
        q = (
            self.stmt()
            .options(noload(Customer.addresses), noload(Customer.favorites))
            .order_by(Customer.created_at.desc())
        )
        if status:
            q = q.where(Customer.verification_status == status)
        return await self.all(q.offset((page - 1) * page_size).limit(page_size))

    async def orders_for(self, customer: Customer) -> list:
        """The customer's orders, newest first. Orders are linked by matching
        phone (no FK), so purchases made before signup still show up."""
        # orders' public API itself imports customers (Customer in
        # CreateOrderAction), so a module-scope import here would make
        # customers.__init__ circular — import lazily instead.
        from app.domains.orders import Order

        rows = await self.db.execute(
            select(Order)
            .where(Order.phone == customer.phone)
            .order_by(Order.created_at.desc())
        )
        return list(rows.scalars().all())
