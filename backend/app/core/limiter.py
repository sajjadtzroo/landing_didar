from slowapi import Limiter

from app.core.config import settings
from app.core.security import get_client_ip

# Key on the real client IP (X-Forwarded-For aware) — not request.client.host,
# which is the proxy's IP behind an ingress and would make one shared bucket.
# Param MUST be named `request`: slowapi injects it by inspecting the name.
#
# Storage: Redis when REDIS_URL is set, so limits are exact and shared across
# workers/instances (in-memory buckets are per-worker => limits ~×N otherwise).
# Fails open: on Redis errors slowapi falls back to in-memory and never blocks
# legitimate traffic because the store is down.
limiter = Limiter(
    key_func=lambda request: get_client_ip(request) or "anon",
    storage_uri=settings.redis_url or "memory://",
    in_memory_fallback_enabled=bool(settings.redis_url),
    swallow_errors=True,
)
