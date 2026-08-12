"""Customer-session Depends. Moved verbatim from app/api/deps.py during the
domain migration — the customers domain owns customer-session resolution."""

import uuid

from fastapi import Depends, HTTPException, Request, status

from app.core.security import CUSTOMER_COOKIE, read_customer_session


def optional_customer(request: Request) -> uuid.UUID | None:
    """Session id if a valid customer cookie is present, else None (guest)."""
    cid = read_customer_session(request.cookies.get(CUSTOMER_COOKIE))
    return uuid.UUID(cid) if cid else None


def require_customer(request: Request) -> uuid.UUID:
    cid = read_customer_session(request.cookies.get(CUSTOMER_COOKIE))
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return uuid.UUID(cid)


CustomerId = Depends(require_customer)
