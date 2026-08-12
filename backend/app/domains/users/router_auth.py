from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.limiter import limiter
from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    SESSION_COOKIE,
    issue_session,
    verify_password_async,
)
from app.domains.users.dependencies import resolve_admin
from app.domains.users.models import AuditLog, User
from app.domains.users.schemas import LoginIn, MeOut

router = APIRouter()


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/login", response_model=MeOut)
@limiter.limit("10/minute")  # brute-force guard; argon2 already slows each try
async def login(
    request: Request,
    payload: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Named users first; the env-var admin stays as a zero-config bootstrap
    superadmin. Both outcomes are audited (login is the one mutation the audit
    middleware can't attribute — there's no cookie yet)."""
    role = None
    user = (
        await db.execute(
            select(User).where(User.username == payload.username, User.is_active)
        )
    ).scalar_one_or_none()
    if user is not None and await verify_password_async(payload.password, user.password_hash):
        role = user.role.value
    elif payload.username == settings.admin_username and await verify_password_async(
        payload.password, settings.admin_password_hash
    ):
        role = "superadmin"

    db.add(
        AuditLog(
            actor=payload.username[:60],
            action="auth.login",
            status=200 if role else 401,
        )
    )
    await db.commit()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    _set_cookie(response, issue_session(payload.username))
    return MeOut(username=payload.username, role=role)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"detail": "ok"}


@router.get("/me", response_model=MeOut)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    ident = await resolve_admin(request, db)
    if ident is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    username, role = ident
    return MeOut(username=username, role=role.value)
