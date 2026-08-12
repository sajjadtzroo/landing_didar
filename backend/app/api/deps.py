# DEPRECATED: admin/agent auth deps moved to app.domains.users — this shim
# keeps old import paths working for not-yet-migrated routers. Remove in the
# final migration step (step 10).
import uuid

from fastapi import Depends, HTTPException, Request, status

from app.core.security import CUSTOMER_COOKIE, read_customer_session
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


def require_customer(request: Request) -> uuid.UUID:
    cid = read_customer_session(request.cookies.get(CUSTOMER_COOKIE))
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return uuid.UUID(cid)


CustomerId = Depends(require_customer)
