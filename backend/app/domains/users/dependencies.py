"""Admin/agent auth Depends. Moved verbatim from app/api/deps.py during the
domain migration — the users domain owns session→role resolution."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE, read_session
from app.domains.users.models import AdminRole, User


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


async def require_agent(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    """Field-sales endpoints (WO 7.5). Returns the full User row (endpoints need
    the id for assignment scoping). Superadmin passes for oversight/debugging."""
    username = read_session(request.cookies.get(SESSION_COOKIE))
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user = (
        await db.execute(
            select(User).where(User.username == username, User.is_active)
        )
    ).scalar_one_or_none()
    if user is None or user.role not in {AdminRole.agent, AdminRole.superadmin}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


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
