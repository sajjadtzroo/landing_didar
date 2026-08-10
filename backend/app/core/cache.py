"""Shared cache: Redis when REDIS_URL is set, in-process dict otherwise.

One tiny surface (`cache_get/cache_set/cache_delete`) so the catalog + gold-price
caches and their bust functions work identically single-node (dict, today's
behavior) and multi-node (Redis). Values are JSON via `jsonable_encoder`, so both
backends hand back the same plain dict/list shapes and FastAPI response_models
re-validate them.

Fail-open by design: any Redis error is logged, Redis is skipped for a short
backoff window, and callers just see a cache miss (the DB serves). Nothing
critical ever lives here — Postgres stays the source of truth.
"""

import json
import time
from typing import Any

from fastapi.encoders import jsonable_encoder
from loguru import logger

from app.core.config import settings

_BACKOFF = 10.0  # seconds to skip Redis after an error (the circuit breaker)

# --- in-process backend (default; also the fallback data path is simply "miss") ---
_local: dict[str, tuple[float, Any]] = {}

# --- redis backend, created lazily so importing this module never connects ---
_redis = None
_down_until = 0.0


def _client():
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
    return _redis


def _redis_ok() -> bool:
    return bool(settings.redis_url) and time.monotonic() >= _down_until


def _mark_down(exc: Exception) -> None:
    global _down_until
    _down_until = time.monotonic() + _BACKOFF
    logger.warning("cache: redis unavailable, failing open for {}s ({})", _BACKOFF, exc)


async def cache_get(key: str) -> Any | None:
    if _redis_ok():
        try:
            raw = await _client().get(key)
            return None if raw is None else json.loads(raw)
        except Exception as e:  # noqa: BLE001 — fail open: treat as a miss
            _mark_down(e)
            return None
    hit = _local.get(key)
    return hit[1] if hit and hit[0] > time.monotonic() else None


async def cache_set(key: str, value: Any, ttl: float) -> None:
    encoded = jsonable_encoder(value)
    if _redis_ok():
        try:
            await _client().set(key, json.dumps(encoded), ex=int(ttl))
            return
        except Exception as e:  # noqa: BLE001
            _mark_down(e)
            return
    _local[key] = (time.monotonic() + ttl, encoded)


async def cache_delete(*keys: str) -> None:
    if _redis_ok():
        try:
            await _client().delete(*keys)
            return
        except Exception as e:  # noqa: BLE001 — worst case: stale until TTL
            _mark_down(e)
            return
    for k in keys:
        _local.pop(k, None)


def clear_all() -> None:
    """Test hook: wipe the in-process backend (tests run with REDIS_URL unset)."""
    _local.clear()
