from typing import Protocol

from app.models.order import Order


def format_order_message(order: Order, admin_url: str) -> str:
    lines = [
        f"سفارش جدید | New order {order.reference}",
        f"{order.full_name} — {order.phone}",
        f"فروشگاه: {order.store_name} ({order.province})",
    ]
    for it in order.items:
        price = "—" if it.unit_price is None else f"{int(it.unit_price):,}"
        lines.append(f"• {it.product_name} ×{it.quantity} @ {price}")
    lines.append(f"جمع: {int(order.total):,}")
    lines.append(f"{admin_url}/{order.id}")
    return "\n".join(lines)


class NotificationAdapter(Protocol):
    async def send_new_order(self, order: Order, admin_url: str) -> None:
        """Notify the admin of a new order. Must not raise on transport failure
        in a way that reaches the request — the caller runs this in a background
        task and swallows/logs errors."""
        ...
