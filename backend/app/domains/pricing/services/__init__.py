"""Stateless TGJU integration: scrape, parse, cache, background refresh."""

from app.domains.pricing.services.tgju import (
    REFRESH_INTERVAL,
    SYMBOLS,
    TGJU_URL,
    get_gold_prices,
    refresh_loop,
)

__all__ = [
    "REFRESH_INTERVAL",
    "SYMBOLS",
    "TGJU_URL",
    "get_gold_prices",
    "refresh_loop",
]
