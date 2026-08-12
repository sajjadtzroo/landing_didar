"""Customers domain: OTP auth, profile, addresses, favorites, verification.

PUBLIC API — the only surface other code may import from."""

from app.domains.customers.dependencies import (
    CustomerId,
    optional_customer,
    require_customer,
)
from app.domains.customers.models import (
    Customer,
    CustomerAddress,
    CustomerVerificationStatus,
    Favorite,
    OtpCode,
)

__all__ = [
    "Customer",
    "CustomerAddress",
    "CustomerId",
    "CustomerVerificationStatus",
    "Favorite",
    "OtpCode",
    "optional_customer",
    "require_customer",
]
