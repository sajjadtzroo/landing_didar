"""Catalog cache keys + busts.

The public product list is cached per (page, page_size) —
`cache:products:v{n}:p{page}:s{size}` — so exact-key deletion can't bust the
paginated variants. Instead the version segment `v{n}` is bumped on every
product mutation: old keys become unreachable and expire by TTL. Best-sellers
is a single key, deleted directly.
"""

from app.core.cache import cache_delete, cache_get, cache_set

_VER_KEY = "cache:products:ver"
_BEST_SELLERS_KEY = "cache:best-sellers"
# The version key must outlive the data keys or a restart/eviction would
# resurrect stale variants; 1 day ≫ the 60s data TTL.
_VER_TTL = 86400.0


async def products_cache_key(page: int | None, page_size: int) -> str:
    ver = await cache_get(_VER_KEY) or 0
    suffix = f"p{page}:s{page_size}" if page else "all"
    return f"cache:products:v{ver}:{suffix}"


async def bust_products_cache() -> None:
    """After any product mutation: new version (unreachable old pages) and
    drop the sales ranking (it embeds product fields)."""
    ver = await cache_get(_VER_KEY) or 0
    await cache_set(_VER_KEY, ver + 1, _VER_TTL)
    await cache_delete(_BEST_SELLERS_KEY)
