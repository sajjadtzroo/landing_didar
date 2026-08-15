from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.domains.orders import Order, OrderItem, OrderStatus
from app.shared.cqrs import BaseQuery


class DashboardQuery(BaseQuery[Order]):
    """Read-only KPI aggregation for the admin dashboard.

    ``model = Order`` because every stat aggregates the orders domain today;
    new sources (customers, serials, ...) get their own named readers here,
    always via the source domain's public API.
    """

    model = Order

    async def count_since(self, ts: datetime) -> int:
        return await self.db.scalar(
            select(func.count()).select_from(Order).where(Order.created_at >= ts)
        ) or 0

    async def stats(self) -> dict:
        """The full admin dashboard read model — one dict, ready to serialize."""
        now = datetime.now(UTC)
        day = now - timedelta(days=1)
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        top = await self.db.execute(
            select(OrderItem.product_name, func.sum(OrderItem.quantity).label("qty"))
            .group_by(OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
        )
        by_province = await self.db.execute(
            select(Order.province, func.count().label("n"))
            .group_by(Order.province)
            .order_by(func.count().desc())
        )

        # All scalar KPIs in ONE pass over orders (count(*) FILTER (...)) —
        # this endpoint is polled by the admin SPA; 8 separate round-trips
        # were the bulk of its latency.
        scalars = (
            await self.db.execute(
                select(
                    func.count(),
                    func.count().filter(
                        Order.status.in_(
                            [OrderStatus.confirmed, OrderStatus.shipped]
                        )
                    ),
                    func.coalesce(func.sum(Order.total), 0),
                    func.count().filter(~Order.is_read),
                    func.count().filter(Order.created_at >= day),
                    func.count().filter(Order.created_at >= week),
                    func.count().filter(Order.created_at >= month),
                )
            )
        ).one()
        (
            total_orders,
            confirmed,
            total_value,
            unread,
            orders_today,
            orders_week,
            orders_month,
        ) = scalars

        # --- Orders per day, last 14 days (zero-filled so the line is continuous) ---
        since = now - timedelta(days=13)
        day_rows = await self.db.execute(
            select(
                func.date_trunc("day", Order.created_at).label("d"),
                func.count().label("n"),
            )
            .where(Order.created_at >= since.replace(hour=0, minute=0, second=0))
            .group_by("d")
        )
        day_counts = {r.d.date().isoformat(): int(r.n) for r in day_rows}
        orders_by_day = [
            {
                "date": (now - timedelta(days=i)).date().isoformat(),
                "count": day_counts.get(
                    (now - timedelta(days=i)).date().isoformat(), 0
                ),
            }
            for i in range(13, -1, -1)
        ]

        # --- Orders by status (all statuses, zero-filled) ---
        status_rows = await self.db.execute(
            select(Order.status, func.count().label("n")).group_by(Order.status)
        )
        status_counts = {s: int(n) for s, n in status_rows.all()}
        by_status = [
            {"status": s.value, "count": status_counts.get(s, 0)} for s in OrderStatus
        ]

        return {
            "orders_today": int(orders_today),
            "orders_week": int(orders_week),
            "orders_month": int(orders_month),
            "total_orders": int(total_orders),
            "total_value": float(total_value),  # total grams sold
            "unread": int(unread),
            "conversion_rate": (
                round(confirmed / total_orders, 3) if total_orders else 0
            ),
            "orders_by_day": orders_by_day,
            "by_status": by_status,
            "top_products": [{"name": n, "quantity": int(q)} for n, q in top.all()],
            "by_province": [{"province": p, "count": n} for p, n in by_province.all()],
        }
