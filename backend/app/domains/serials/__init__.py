"""Serials domain: per-piece authenticity codes, scan logging, QR labels —
plus warranty activation and buyback requests (merged here: warranty/buyback
are serial-lifecycle events; the passport endpoint reads all three).

PUBLIC API — the only surface other code may import from."""

from app.domains.serials import service
from app.domains.serials.serial_models import (
    ProductSerial,
    ProductSerialStatus,
    SerialEvent,
    SerialScan,
)
from app.domains.serials.warranty_models import (
    BuybackRequest,
    BuybackStatus,
    Warranty,
)

__all__ = [
    "BuybackRequest",
    "BuybackStatus",
    "ProductSerial",
    "ProductSerialStatus",
    "SerialEvent",
    "SerialScan",
    "Warranty",
    "service",
]
