"""Orders domain: checkout, tracking, admin order management, order alerts.

PUBLIC API — the only surface other code may import from."""

from app.domains.orders.actions import CreateOrderAction, OrderAction
from app.domains.orders.models import (
    ContactMethod,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusLog,
)
from app.domains.orders.queries import OrderQuery
from app.domains.orders.schemas import (
    PHONE_RE,
    DeliveryProof,
    OrderCreate,
    OrderItemIn,
    OrderTrackOut,
)
from app.shared.validation import hash_ip

__all__ = [
    "PHONE_RE",
    "ContactMethod",
    "CreateOrderAction",
    "DeliveryProof",
    "Order",
    "OrderAction",
    "OrderCreate",
    "OrderItem",
    "OrderItemIn",
    "OrderQuery",
    "OrderStatus",
    "OrderStatusLog",
    "OrderTrackOut",
    "hash_ip",
]
