"""Browser/Nitro error ingest (nuxt.* namespaces). The frontend batches its
captured errors here so client-side failures reach the same Loki pipeline as
server logs. Strictly bounded payloads + rate limit: this is a public endpoint
and must never become a log-injection or flooding vector."""

from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.api.limiter import limiter
from app.core.logging import get_logger

router = APIRouter()

_LEVELS = {"info": "INFO", "warn": "WARNING", "error": "ERROR"}


class ClientLog(BaseModel):
    level: Literal["info", "warn", "error"] = "error"
    module: str = Field("nuxt.client", max_length=40, pattern=r"^[a-z0-9_.\-]+$")
    event: str = Field(max_length=80, pattern=r"^[a-z0-9_.\-]+$")
    message: str = Field("", max_length=2000)
    url: str | None = Field(None, max_length=500)
    stack: str | None = Field(None, max_length=4000)


class ClientLogBatch(BaseModel):
    logs: list[ClientLog] = Field(max_length=20)


@router.post("/logs", status_code=204)
@limiter.limit("30/minute")
async def ingest_client_logs(request: Request, payload: ClientLogBatch):
    for entry in payload.logs:
        module = entry.module if entry.module.startswith("nuxt.") else "nuxt.client"
        get_logger(module).bind(
            event=entry.event, url=entry.url, stack=entry.stack
        ).log(_LEVELS[entry.level], "{}", entry.message)
    return Response(status_code=204)
