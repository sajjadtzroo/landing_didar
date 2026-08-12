from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.domains.orders import Order, OrderItem, OrderStatus

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
    total_value = await db.scalar(select(func.coalesce(func.sum(Order.total), 0))) or 0
    unread = await db.scalar(
        select(func.count()).select_from(Order).where(~Order.is_read)
    ) or 0

    # --- Orders per day, last 14 days (zero-filled so the line is continuous) ---
    since = now - timedelta(days=13)
    day_rows = await db.execute(
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
            "count": day_counts.get((now - timedelta(days=i)).date().isoformat(), 0),
        }
        for i in range(13, -1, -1)
    ]

    # --- Orders by status (all statuses, zero-filled) ---
    status_rows = await db.execute(
        select(Order.status, func.count().label("n")).group_by(Order.status)
    )
    status_counts = {s: int(n) for s, n in status_rows.all()}
    by_status = [
        {"status": s.value, "count": status_counts.get(s, 0)} for s in OrderStatus
    ]

    return {
        "orders_today": await count_since(day),
        "orders_week": await count_since(week),
        "orders_month": await count_since(month),
        "total_orders": int(total_orders),
        "total_value": float(total_value),  # total grams sold
        "unread": int(unread),
        "conversion_rate": round(confirmed / total_orders, 3) if total_orders else 0,
        "orders_by_day": orders_by_day,
        "by_status": by_status,
        "top_products": [{"name": n, "quantity": int(q)} for n, q in top.all()],
        "by_province": [{"province": p, "count": n} for p, n in by_province.all()],
    }
