from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import require_admin
from app.core.config import settings
from app.core.security import (
    SESSION_COOKIE,
    issue_session,
    verify_password,
)
from app.schemas.auth import LoginIn, MeOut

router = APIRouter()


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=MeOut)
async def login(payload: LoginIn, response: Response):
    ok = payload.username == settings.admin_username and verify_password(
        payload.password, settings.admin_password_hash
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    _set_cookie(response, issue_session(payload.username))
    return MeOut(username=payload.username)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"detail": "ok"}


@router.get("/me", response_model=MeOut)
async def me(request: Request):
    return MeOut(username=require_admin(request))
