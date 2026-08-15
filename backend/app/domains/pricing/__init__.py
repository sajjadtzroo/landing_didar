"""Pricing domain: live gold-rate board (TGJU scrape + snapshot persistence).

PUBLIC API — the only surface other code may import from."""

from app.domains.pricing.actions import PriceAction
from app.domains.pricing.models import GoldPriceSnapshot
from app.domains.pricing.queries import PriceQuery
from app.domains.pricing.services import get_gold_prices, refresh_loop

__all__ = [
    "GoldPriceSnapshot",
    "PriceAction",
    "PriceQuery",
    "get_gold_prices",
    "refresh_loop",
]
