from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.limiter import limiter
from app.api.v1 import (
    admin_catalog,
    admin_landings,
    admin_orders,
    admin_stats,
    auth,
    public,
)
from app.core.config import settings
from app.core.logging import setup_logging

# Route everything (app + uvicorn + sqlalchemy) through loguru's single sink.
setup_logging()

app = FastAPI(title="Didar Gold API", version="1.0.0")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# --- Media (dev). Swap LocalStorage for S3 in prod; see services/storage.py ---
media_dir = Path(settings.media_root)
media_dir.mkdir(parents=True, exist_ok=True)
app.mount(settings.media_url_prefix, StaticFiles(directory=media_dir), name="media")


@app.get("/health")
async def health():
    return {"status": "ok"}


API = "/api/v1"
app.include_router(public.router, prefix=API, tags=["public"])
app.include_router(auth.router, prefix=f"{API}/admin", tags=["auth"])
app.include_router(admin_orders.router, prefix=f"{API}/admin", tags=["admin:orders"])
app.include_router(admin_catalog.router, prefix=f"{API}/admin", tags=["admin:catalog"])
app.include_router(
    admin_landings.router, prefix=f"{API}/admin", tags=["admin:landings"]
)
app.include_router(admin_stats.router, prefix=f"{API}/admin", tags=["admin:stats"])
