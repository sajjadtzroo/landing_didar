from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.order import Order, OrderItem, OrderStatus

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(UTC)
    day = now - timedelta(days=1)
    week = now - timedelta(days=7)
    month = now - timedelta(days=30)

    async def count_since(ts: datetime) -> int:
        return await db.scalar(
            select(func.count()).select_from(Order).where(Order.created_at >= ts)
        ) or 0

    top = await db.execute(
        select(OrderItem.product_name, func.sum(OrderItem.quantity).label("qty"))
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    by_province = await db.execute(
        select(Order.province, func.count().label("n"))
        .group_by(Order.province)
        .order_by(func.count().desc())
    )

    total_orders = await db.scalar(select(func.count()).select_from(Order)) or 0
    confirmed = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.status.in_([OrderStatus.confirmed, OrderStatus.shipped]))
    ) or 0

    return {
        "orders_today": await count_since(day),
        "orders_week": await count_since(week),
        "orders_month": await count_since(month),
        "top_products": [{"name": n, "quantity": int(q)} for n, q in top.all()],
        "by_province": [{"province": p, "count": n} for p, n in by_province.all()],
        "conversion_rate": round(confirmed / total_orders, 3) if total_orders else 0,
    }
