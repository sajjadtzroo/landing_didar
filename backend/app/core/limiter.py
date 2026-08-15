from slowapi import Limiter

from app.core.config import settings
from app.core.security import get_client_ip

# Key on the real client IP (X-Forwarded-For aware) — not request.client.host,
# which is the proxy's IP behind an ingress and would make one shared bucket.
# Param MUST be named `request`: slowapi injects it by inspecting the name.
#
# Storage: Redis when configured, so limits are exact and shared across
# workers/instances (in-memory buckets are per-worker => limits ~×N otherwise).
# RATELIMIT_REDIS_URL points at a noeviction instance — sharing the LRU cache
# Redis lets cache pressure evict the counters and silently reset the limits.
# Fails open: on Redis errors slowapi falls back to in-memory and never blocks
# legitimate traffic because the store is down.
_storage = settings.ratelimit_redis_url or settings.redis_url
limiter = Limiter(
    key_func=lambda request: get_client_ip(request) or "anon",
    storage_uri=_storage or "memory://",
    in_memory_fallback_enabled=bool(_storage),
    swallow_errors=True,
)
