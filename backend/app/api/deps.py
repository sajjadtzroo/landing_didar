import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    CUSTOMER_COOKIE,
    SESSION_COOKIE,
    read_customer_session,
    read_session,
)
from app.models.user import AdminRole, User


def get_client_ip(request: Request) -> str | None:
    # Behind a proxy, X-Forwarded-For's first hop is the client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


async def resolve_admin(
    request: Request, db: AsyncSession
) -> tuple[str, AdminRole] | None:
    """Session cookie -> (username, role). Role is resolved fresh per request so
    deactivation / role changes bite immediately. The env-var admin resolves as a
    bootstrap superadmin without touching the DB."""
    username = read_session(request.cookies.get(SESSION_COOKIE))
    if not username:
        return None
    if username == settings.admin_username:
        return username, AdminRole.superadmin
    user = (
        await db.execute(
            select(User).where(User.username == username, User.is_active)
        )
    ).scalar_one_or_none()
    if user is None:
        return None
    return user.username, user.role


_PANEL_ROLES = {AdminRole.superadmin, AdminRole.operator}


async def require_admin(
    request: Request, db: AsyncSession = Depends(get_db)
) -> str:
    ident = await resolve_admin(request, db)
    if ident is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    username, role = ident
    if role not in _PANEL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return username


async def require_superadmin(
    request: Request, db: AsyncSession = Depends(get_db)
) -> str:
    ident = await resolve_admin(request, db)
    if ident is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    username, role = ident
    if role != AdminRole.superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return username


AdminUser = Depends(require_admin)


def require_customer(request: Request) -> uuid.UUID:
    cid = read_customer_session(request.cookies.get(CUSTOMER_COOKIE))
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return uuid.UUID(cid)


CustomerId = Depends(require_customer)
