"""Orders domain: checkout, tracking, admin order management, order alerts.

PUBLIC API — the only surface other code may import from."""

from app.domains.orders.models import (
    ContactMethod,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusLog,
)
from app.domains.orders.schemas import (
    PHONE_RE,
    DeliveryProof,
    OrderCreate,
    OrderItemIn,
    OrderTrackOut,
)
from app.domains.orders.service import hash_ip

__all__ = [
    "PHONE_RE",
    "ContactMethod",
    "DeliveryProof",
    "Order",
    "OrderCreate",
    "OrderItem",
    "OrderItemIn",
    "OrderStatus",
    "OrderStatusLog",
    "OrderTrackOut",
    "hash_ip",
]
