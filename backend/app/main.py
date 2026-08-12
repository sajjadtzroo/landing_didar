import asyncio
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.limiter import limiter
from app.api.v1 import client_logs
from app.core.config import settings
from app.core.db import engine
from app.core.logging import get_logger, setup_logging
from app.core.metrics import (
    HTTP_DURATION,
    HTTP_REQUESTS,
    RATELIMIT_TRIPS,
    metrics_endpoint,
)
from app.domains.agents.router_admin_gallery import router as agents_admin_gallery
from app.domains.agents.router_agent import router as agents_agent
from app.domains.catalog.router_admin import router as catalog_admin
from app.domains.catalog.router_public import router as catalog_public
from app.domains.content.router_admin_faqs import router as content_admin_faqs
from app.domains.content.router_admin_landings import router as content_admin_landings
from app.domains.content.router_admin_portfolios import (
    router as content_admin_portfolios,
)
from app.domains.content.router_public import router as content_public
from app.domains.customers.router_account import router as customers_account
from app.domains.customers.router_admin import router as customers_admin
from app.domains.dashboard.router_admin import router as dashboard_admin
from app.domains.orders.router_admin import router as orders_admin
from app.domains.orders.router_public import router as orders_public
from app.domains.pricing import refresh_loop
from app.domains.pricing.router_admin import router as pricing_admin
from app.domains.pricing.router_public import router as pricing_public
from app.domains.serials.router_admin import router as serials_admin
from app.domains.serials.router_admin_buybacks import router as serials_admin_buybacks
from app.domains.serials.router_public import router as serials_public
from app.domains.users.router_admin_audit import router as users_admin_audit
from app.domains.users.router_admin_users import router as users_admin_users
from app.domains.users.router_auth import router as users_auth

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
        from app.domains.users import AuditLog

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


# --- Request context: X-Request-ID + one access record + metrics per request ---
# Added after the audit middleware so it runs OUTERMOST: every log line emitted
# while handling the request (handlers, services, audit) carries the request_id.
_access_log = get_logger("api.access")
_error_log = get_logger("api.error")
_UNLOGGED_PATHS = {"/health", "/ready", "/metrics"}


@app.middleware("http")
async def request_context(request: Request, call_next):
    from loguru import logger as _logger

    rid = (request.headers.get("X-Request-ID") or uuid.uuid4().hex)[:64]
    start = time.perf_counter()
    with _logger.contextualize(request_id=rid):
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 — last-resort: log with context, 500 envelope
            duration = round((time.perf_counter() - start) * 1000, 1)
            _error_log.bind(
                event="api.error.unhandled",
                status_code=500,
                duration_ms=duration,
            ).opt(exception=True).error(
                "{} {} failed", request.method, request.url.path
            )
            route = request.scope.get("route")
            HTTP_REQUESTS.labels(
                request.method, route.path if route else "unmatched", "500"
            ).inc()
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "field": None},
                headers={"X-Request-ID": rid},
            )
        duration = round((time.perf_counter() - start) * 1000, 1)
        path = request.url.path
        route = request.scope.get("route")
        route_path = route.path if route else "unmatched"
        if path not in _UNLOGGED_PATHS and not path.startswith(
            settings.media_url_prefix + "/"
        ):
            HTTP_REQUESTS.labels(
                request.method, route_path, str(response.status_code)
            ).inc()
            HTTP_DURATION.labels(request.method, route_path).observe(duration / 1000)
            _access_log.bind(
                event="http.request",
                status_code=response.status_code,
                duration_ms=duration,
            ).info("{} {} -> {}", request.method, path, response.status_code)
        response.headers["X-Request-ID"] = rid
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
    from app.api.deps import get_client_ip

    route = request.scope.get("route")
    RATELIMIT_TRIPS.labels(route.path if route else "unmatched").inc()
    get_logger("security").bind(
        event="security.ratelimit.tripped", status_code=429
    ).warning("rate limit on {} from {}", request.url.path, get_client_ip(request))
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


@app.get("/ready")
async def ready():
    """Readiness: DB + Redis (when configured). Fails while a dependency is
    down so an orchestrator/proxy stops routing traffic here."""
    checks = {"db": "ok", "redis": "ok" if settings.redis_url else "disabled"}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        checks["db"] = "down"
    if settings.redis_url:
        try:
            from app.core import cache as _cache

            await asyncio.wait_for(_cache._client().ping(), timeout=1.0)
        except Exception:  # noqa: BLE001
            checks["redis"] = "down"
    if "down" in checks.values():
        raise HTTPException(503, detail=checks)
    return checks


@app.get("/metrics")
async def metrics():
    """Prometheus scrape target (aggregates across gunicorn workers when
    PROMETHEUS_MULTIPROC_DIR is set)."""
    return metrics_endpoint()


API = "/api/v1"
app.include_router(catalog_public, prefix=API, tags=["public"])
app.include_router(orders_public, prefix=API, tags=["public"])
app.include_router(serials_public, prefix=API, tags=["public"])
app.include_router(content_public, prefix=API, tags=["public"])
app.include_router(pricing_public, prefix=API, tags=["public"])
app.include_router(client_logs.router, prefix=API, tags=["client-logs"])
app.include_router(customers_account, prefix=f"{API}/account", tags=["account"])
app.include_router(users_auth, prefix=f"{API}/admin", tags=["auth"])
app.include_router(orders_admin, prefix=f"{API}/admin", tags=["admin:orders"])
app.include_router(catalog_admin, prefix=f"{API}/admin", tags=["admin:catalog"])
app.include_router(
    content_admin_faqs, prefix=f"{API}/admin", tags=["admin:catalog"]
)
app.include_router(
    content_admin_landings, prefix=f"{API}/admin", tags=["admin:landings"]
)
app.include_router(
    content_admin_portfolios, prefix=f"{API}/admin", tags=["admin:portfolios"]
)
app.include_router(dashboard_admin, prefix=f"{API}/admin", tags=["admin:stats"])
app.include_router(pricing_admin, prefix=f"{API}/admin", tags=["admin:prices"])
app.include_router(serials_admin, prefix=f"{API}/admin", tags=["admin:serials"])
app.include_router(
    customers_admin, prefix=f"{API}/admin", tags=["admin:customers"]
)
app.include_router(users_admin_users, prefix=f"{API}/admin", tags=["admin:users"])
app.include_router(users_admin_audit, prefix=f"{API}/admin", tags=["admin:audit"])
app.include_router(agents_agent, prefix=f"{API}/agent", tags=["agent"])
app.include_router(serials_admin_buybacks, prefix=f"{API}/admin", tags=["admin:buybacks"])
app.include_router(agents_admin_gallery, prefix=f"{API}/admin", tags=["admin:gallery"])
