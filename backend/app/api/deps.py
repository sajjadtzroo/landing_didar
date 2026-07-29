from fastapi import Depends, HTTPException, Request, status

from app.core.security import SESSION_COOKIE, read_session


def get_client_ip(request: Request) -> str | None:
    # Behind a proxy, X-Forwarded-For's first hop is the client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def require_admin(request: Request) -> str:
    username = read_session(request.cookies.get(SESSION_COOKIE))
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return username


AdminUser = Depends(require_admin)
