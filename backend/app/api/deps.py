# DEPRECATED: auth deps moved to app.domains.users / app.domains.customers —
# this shim keeps old import paths working for not-yet-migrated routers.
# Remove in the final migration step (step 10).
from fastapi import Request

from app.domains.customers import (  # noqa: F401
    CustomerId,
    require_customer,
)
from app.domains.users import (  # noqa: F401
    AdminUser,
    require_admin,
    require_agent,
    require_superadmin,
    resolve_admin,
)


def get_client_ip(request: Request) -> str | None:
    # Behind a proxy, X-Forwarded-For's first hop is the client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
