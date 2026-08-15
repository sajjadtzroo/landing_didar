"""Public-cache busting — stateless integration helpers over app.core.cache.

Moved verbatim from app/api/v1/public.py during the domain migration; the
group→product resolution that used to live alongside these moved to
queries/product_groups.py in the CQRS split (it reads the DB)."""

from app.core.cache import cache_delete


async def bust_landing_cache(slug: str) -> None:
    """Drop a landing's cached payload so an admin edit shows immediately instead
    of after the TTL. Called by LandingAction on mutate."""
    await cache_delete(f"cache:landing:{slug}")


async def bust_portfolios_cache() -> None:
    """Drop the cached /portfolios payload so an admin edit shows immediately.
    Called by PortfolioAction on mutate."""
    await cache_delete("cache:portfolios")


async def bust_portfolio_cache(slug: str) -> None:
    """Drop a single portfolio's cached detail payload. Called by PortfolioAction
    on mutate (alongside bust_portfolios_cache for the list)."""
    await cache_delete(f"cache:portfolio:{slug}")
