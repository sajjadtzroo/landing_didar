"""Live gold/currency prices scraped from TGJU.

TGJU exposes the whole board as one JSON blob (call.tgju.org/ajax.json). We pull a
curated set of symbols, convert Rial→Toman (the site's Toman figures = Rial/10),
and cache in-process for a short TTL so the admin panel can poll without hammering
TGJU. On a fetch failure we serve the last good snapshot (marked stale).
ponytail: dict cache; TGJU covers every index the panel shows, so no second source.
"""

import asyncio
import time

import httpx
from loguru import logger

TGJU_URL = "https://call.tgju.org/ajax.json"
_TTL = 90.0  # seconds; TGJU updates every few seconds but the panel polls ~60s
REFRESH_INTERVAL = 120  # background refresh cadence (see refresh_loop)
_HEADERS = {"User-Agent": "Mozilla/5.0"}

# (tgju key, Persian label, unit). Order = display order. unit 'toman' => Rial/10.
SYMBOLS: list[tuple[str, str, str]] = [
    ("geram18", "طلای ۱۸ عیار (هر گرم)", "toman"),
    ("geram24", "طلای ۲۴ عیار (هر گرم)", "toman"),
    ("mesghal", "مثقال طلا", "toman"),
    ("gold_futures", "آبشده", "toman"),
    ("sekee", "سکه امامی", "toman"),
    ("sekeb", "سکه بهار آزادی", "toman"),
    ("nim", "نیم سکه", "toman"),
    ("rob", "ربع سکه", "toman"),
    ("price_dollar_rl", "دلار آزاد", "toman"),
    ("ons", "انس طلا", "usd"),
]

_cache: dict = {"at": 0.0, "items": None}


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _parse(current: dict) -> list[dict]:
    items: list[dict] = []
    for key, label, unit in SYMBOLS:
        v = current.get(key)
        if not isinstance(v, dict):
            continue
        raw = _num(v.get("p"))
        if raw is None:
            continue
        items.append(
            {
                "symbol": key,
                "label": label,
                "unit": unit,
                # Toman figures are Rial/10; USD (ounce) stays as-is.
                "price": round(raw / 10) if unit == "toman" else raw,
                "change_pct": _num(v.get("dp")) or 0.0,
                "direction": v.get("dt") or "none",  # high | low | none
                "updated_at": v.get("t"),  # HH:MM:SS (Persian digits from TGJU)
            }
        )
    return items


async def get_gold_prices(force: bool = False) -> dict:
    """Return {items, source, cached, stale?, error?}. Cached within _TTL."""
    now = time.monotonic()
    if not force and _cache["items"] and now - _cache["at"] < _TTL:
        return {"items": _cache["items"], "source": "tgju", "cached": True}
    try:
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
            resp = await client.get(TGJU_URL)
            resp.raise_for_status()
            current = resp.json().get("current", {})
        items = _parse(current)
        if not items:
            raise ValueError("no known symbols in TGJU payload")
        _cache["at"], _cache["items"] = now, items
        return {"items": items, "source": "tgju", "cached": False}
    except Exception as e:  # noqa: BLE001 — never break the admin panel on a scrape error
        logger.warning("gold prices fetch failed: {}", e)
        if _cache["items"]:
            return {"items": _cache["items"], "source": "tgju", "cached": True, "stale": True}
        return {"items": [], "source": "tgju", "error": True}


async def refresh_loop() -> None:
    """Background task (started by the app lifespan): force-scrape TGJU every
    REFRESH_INTERVAL seconds so the board stays warm and scraper failures surface
    in the logs — the "check every 2 minutes" baked into the running app.
    ponytail: one loop per worker (gunicorn -w 2 => 2 scrapes/interval), fine at
    this volume; gate to a single worker if the call rate ever matters.
    """
    while True:
        try:
            d = await get_gold_prices(force=True)
            if d.get("error"):
                logger.warning("gold refresh: scraper returned no data")
            else:
                logger.info(
                    "gold refresh: {} symbols (stale={})",
                    len(d["items"]),
                    d.get("stale", False),
                )
        except asyncio.CancelledError:
            raise  # clean shutdown
        except Exception:  # noqa: BLE001 — a bad iteration must not kill the loop
            logger.exception("gold refresh loop iteration failed")
        await asyncio.sleep(REFRESH_INTERVAL)
