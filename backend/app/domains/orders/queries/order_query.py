from datetime import datetime
from typing import ClassVar

from sqlalchemy import Select, func, or_, select

from app.domains.catalog import Product
from app.domains.orders.models import Order, OrderItem, OrderStatus
from app.shared.cqrs import BaseQuery


class OrderQuery(BaseQuery[Order]):
    model = Order

    # Whitelisted sort columns (key sent by the admin UI -> column). created_at
    # is the default and also the tiebreaker so paging stays stable.
    _SORTS: ClassVar = {
        "created_at": Order.created_at,
        "total": Order.total,
        "full_name": Order.full_name,
        "status": Order.status,
        "reference": Order.reference,
    }

    def admin_filter(
        self,
        *,
        status: OrderStatus | None = None,
        province: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        q: str | None = None,
    ) -> Select[tuple[Order]]:
        stmt = self.stmt()
        if status:
            stmt = stmt.where(Order.status == status)
        if province:
            stmt = stmt.where(Order.province == province)
        if date_from:
            stmt = stmt.where(Order.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Order.created_at <= date_to)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Order.reference.ilike(like),
                    Order.full_name.ilike(like),
                    Order.phone.ilike(like),
                    Order.store_name.ilike(like),
                )
            )
        return stmt

    def admin_order_by(self, sort: str, direction: str) -> tuple:
        col = self._SORTS.get(sort, Order.created_at)
        primary = col.asc() if direction == "asc" else col.desc()
        return (primary, Order.created_at.desc())

    async def admin_export(
        self,
        *,
        status: OrderStatus | None = None,
        province: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        q: str | None = None,
    ) -> list[Order]:
        stmt = self.admin_filter(
            status=status, province=province, date_from=date_from, date_to=date_to, q=q
        )
        return await self.all(stmt.order_by(Order.created_at.desc()))

    async def unread_count(self) -> int:
        n = await self.db.scalar(
            select(func.count()).select_from(Order).where(~Order.is_read)
        )
        return n or 0

    async def by_reference(self, reference: str) -> Order | None:
        return await self.one_or_none(
            self.stmt().where(Order.reference == reference.strip())
        )

    async def by_idempotency_key(self, key: str) -> Order | None:
        if not key:
            return None
        return await self.one_or_none(self.stmt().where(Order.idempotency_key == key))

    async def best_seller_products(self, limit: int = 8) -> list[Product]:
        """Top products by units actually sold (order_items, non-cancelled
        orders). Lives here because sales data does."""
        rows = await self.db.execute(
            select(Product)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Product.is_active,
                Product.product_status != "not_for_sale",
                Order.status != OrderStatus.cancelled,
            )
            .group_by(Product.id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
        )
        return list(rows.scalars().all())
