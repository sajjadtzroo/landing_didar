"""Serials domain: per-piece authenticity codes, scan logging, QR labels —
plus warranty activation and buyback requests (merged here: warranty/buyback
are serial-lifecycle events; the passport endpoint reads all three).

PUBLIC API — the only surface other code may import from."""

from app.domains.serials.actions import (
    ActivateWarrantyAction,
    BuybackAction,
    SerialAction,
)
from app.domains.serials.models import (
    BuybackRequest,
    BuybackStatus,
    ProductSerial,
    ProductSerialStatus,
    SerialEvent,
    SerialScan,
    Warranty,
)
from app.domains.serials.queries import BuybackQuery, SerialQuery, WarrantyQuery
from app.domains.serials.services import format_code, normalize, qr_png

__all__ = [
    "ActivateWarrantyAction",
    "BuybackAction",
    "BuybackQuery",
    "BuybackRequest",
    "BuybackStatus",
    "ProductSerial",
    "ProductSerialStatus",
    "SerialAction",
    "SerialEvent",
    "SerialQuery",
    "SerialScan",
    "Warranty",
    "WarrantyQuery",
    "format_code",
    "normalize",
    "qr_png",
]
