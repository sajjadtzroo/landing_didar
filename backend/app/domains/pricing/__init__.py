"""Pricing domain: live gold-rate board (TGJU scrape + snapshot persistence).

PUBLIC API — the only surface other code may import from."""

from app.domains.pricing.models import GoldPriceSnapshot
from app.domains.pricing.service import get_gold_prices, refresh_loop

__all__ = ["GoldPriceSnapshot", "get_gold_prices", "refresh_loop"]
