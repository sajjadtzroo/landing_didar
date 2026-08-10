import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.limiter import limiter
from app.api.v1 import (
    account,
    admin_catalog,
    admin_customers,
    admin_landings,
    admin_orders,
    admin_portfolios,
    admin_prices,
    admin_serials,
    admin_stats,
    admin_users,
    admin_audit,
    admin_buybacks,
    admin_gallery,
    agent,
    auth,
    public,
)
from app.core.config import settings
from sqlalchemy import text

from app.core.db import engine
from app.core.logging import setup_logging
from app.services.gold_prices import refresh_loop

# Route everything (app + uvicorn + sqlalchemy) through loguru's single sink.
setup_logging()

# Fail fast if a real (HTTPS/secure-cookie) deploy is running on a known default
# secret — the session cookie is signed with it, so a default = forgeable admin.
_WEAK_SECRETS = {"", "change-me-in-prod", "dev-secret-change-me"}
if settings.cookie_secure and (
    settings.secret_key in _WEAK_SECRETS or len(settings.secret_key) < 24
):
    raise RuntimeError(
        "SECRET_KEY must be a strong value (24+ chars) in production"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background: refresh the gold-price board every REFRESH_INTERVAL (2 min).
    gold_task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        gold_task.cancel()
        with suppress(asyncio.CancelledError):
            await gold_task
        await engine.dispose()  # close the pool cleanly on SIGTERM


# Hide the API surface in production (secure cookies == prod); open in dev.
_prod = settings.cookie_secure
app = FastAPI(
    title="Didar Gold API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _prod else "/docs",
    redoc_url=None if _prod else "/redoc",
    openapi_url=None if _prod else "/openapi.json",
)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Large JSON payloads (catalog, admin lists) and CSV exports compress 5-20x.
app.add_middleware(GZipMiddleware, minimum_size=1024)


# --- Audit trail (WO 7.15): every mutating admin request, one middleware ---
_AUDIT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


@app.middleware("http")
async def audit_admin_mutations(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if (
        request.method in _AUDIT_METHODS
        and (path.startswith("/api/v1/admin") or path.startswith("/api/v1/agent"))
        and path != "/api/v1/admin/login"  # audited inside login (no cookie yet)
    ):
        from app.core.db import SessionLocal
        from app.core.security import SESSION_COOKIE, read_session
        from app.models.user import AuditLog

        actor = read_session(request.cookies.get(SESSION_COOKIE))
        if actor:
            try:
                async with SessionLocal() as s:
                    s.add(
                        AuditLog(
                            actor=actor[:60],
                            action=f"{request.method} {path}"[:200],
                            status=response.status_code,
                        )
                    )
                    await s.commit()
            except Exception:  # noqa: BLE001 — auditing must never fail a request
                from loguru import logger

                logger.warning("audit write failed for {} {}", request.method, path)
    return response

# --- Consistent error envelope: {"detail": "...", "field": "..."} everywhere ---


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    err = exc.errors()[0] if exc.errors() else {}
    loc = err.get("loc", [])
    field = loc[-1] if loc else None
    return JSONResponse(
        status_code=422,
        content={"detail": err.get("msg", "Invalid input"), "field": field},
    )


@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later.", "field": None},
    )


# --- Media ---------------------------------------------------------------------
# When MinIO is configured, serve /media by streaming from the PRIVATE bucket with
# credentials (bucket stays private; the app is the only reader), falling back to
# local disk for pre-MinIO / imported files. Otherwise mount the local directory.
media_dir = Path(settings.media_root)
media_dir.mkdir(parents=True, exist_ok=True)

from app.services.storage import MinioStorage, get_storage  # noqa: E402

if isinstance(get_storage(), MinioStorage):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse, StreamingResponse
    from minio.error import S3Error

    @app.get(settings.media_url_prefix + "/{key:path}")
    async def media(key: str):
        if ".." in key or key.startswith("/"):
            raise HTTPException(404, detail="Not found")
        store = get_storage()
        try:
            resp = await asyncio.to_thread(store.open, key)
        except S3Error as exc:
            local = media_dir / key
            if exc.code in ("NoSuchKey", "NoSuchBucket") and local.is_file():
                return FileResponse(local)  # pre-MinIO / imported media
            raise HTTPException(404, detail="Not found") from exc
        ctype = resp.headers.get("Content-Type", "application/octet-stream")

        def _iter():
            try:
                yield from resp.stream(64 * 1024)
            finally:
                resp.close()
                resp.release_conn()

        return StreamingResponse(
            _iter(),
            media_type=ctype,
            headers={"Cache-Control": "private, max-age=300"},
        )
else:
    app.mount(
        settings.media_url_prefix, StaticFiles(directory=media_dir), name="media"
    )


@app.get("/health")
async def health():
    """Liveness + real dependency check (a dead DB should fail the probe)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — any DB failure means unhealthy
        raise HTTPException(503, detail="database unavailable")
    return {"status": "ok"}


API = "/api/v1"
app.include_router(public.router, prefix=API, tags=["public"])
app.include_router(account.router, prefix=f"{API}/account", tags=["account"])
app.include_router(auth.router, prefix=f"{API}/admin", tags=["auth"])
app.include_router(admin_orders.router, prefix=f"{API}/admin", tags=["admin:orders"])
app.include_router(admin_catalog.router, prefix=f"{API}/admin", tags=["admin:catalog"])
app.include_router(
    admin_landings.router, prefix=f"{API}/admin", tags=["admin:landings"]
)
app.include_router(
    admin_portfolios.router, prefix=f"{API}/admin", tags=["admin:portfolios"]
)
app.include_router(admin_stats.router, prefix=f"{API}/admin", tags=["admin:stats"])
app.include_router(admin_prices.router, prefix=f"{API}/admin", tags=["admin:prices"])
app.include_router(admin_serials.router, prefix=f"{API}/admin", tags=["admin:serials"])
app.include_router(
    admin_customers.router, prefix=f"{API}/admin", tags=["admin:customers"]
)
app.include_router(admin_users.router, prefix=f"{API}/admin", tags=["admin:users"])
app.include_router(admin_audit.router, prefix=f"{API}/admin", tags=["admin:audit"])
app.include_router(agent.router, prefix=f"{API}/agent", tags=["agent"])
app.include_router(admin_buybacks.router, prefix=f"{API}/admin", tags=["admin:buybacks"])
app.include_router(admin_gallery.router, prefix=f"{API}/admin", tags=["admin:gallery"])
