"""Customers domain: OTP auth, profile, addresses, favorites, verification.

PUBLIC API — the only surface other code may import from."""

from app.domains.customers.actions import (
    AddressAction,
    CustomerAction,
    FavoriteAction,
    RequestOtpAction,
    VerifyCustomerAction,
    VerifyOtpAction,
)
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
from app.domains.customers.queries import AddressQuery, CustomerQuery, FavoriteQuery

__all__ = [
    "AddressAction",
    "AddressQuery",
    "Customer",
    "CustomerAction",
    "CustomerAddress",
    "CustomerId",
    "CustomerQuery",
    "CustomerVerificationStatus",
    "Favorite",
    "FavoriteAction",
    "FavoriteQuery",
    "OtpCode",
    "RequestOtpAction",
    "VerifyCustomerAction",
    "VerifyOtpAction",
    "optional_customer",
    "require_customer",
]
