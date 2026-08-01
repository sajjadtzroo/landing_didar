from slowapi import Limiter

from app.api.deps import get_client_ip

# Key on the real client IP (X-Forwarded-For aware) — not request.client.host,
# which is the proxy's IP behind an ingress and would make one shared bucket.
# Param MUST be named `request`: slowapi injects it by inspecting the name.
limiter = Limiter(key_func=lambda request: get_client_ip(request) or "anon")
