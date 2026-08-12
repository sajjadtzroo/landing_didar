"""Live gold/currency prices scraped from TGJU.

TGJU exposes the whole board as one JSON blob (call.tgju.org/ajax.json). We pull a
curated set of symbols, convert Rial→Toman (the site's Toman figures = Rial/10),
and cache in-process for a short TTL so the admin panel can poll without hammering
TGJU. On a fetch failure we serve the last good snapshot (marked stale).
ponytail: dict cache; TGJU covers every index the panel shows, so no second source.
"""

import asyncio
from datetime import datetime, timezone

import httpx
from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.cache import cache_get, cache_set
from app.core.db import SessionLocal
from app.domains.pricing.models import GoldPriceSnapshot

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

_CACHE_KEY = "cache:prices:board"  # shared via app.core.cache (dict or Redis)


async def _save_snapshot(items: list[dict], source: str = "tgju") -> None:
    """Upsert the single last-good row (id=1). Never raises — a DB hiccup must not
    break serving live prices."""
    try:
        async with SessionLocal() as s:
            stmt = pg_insert(GoldPriceSnapshot).values(
                id=1, items=items, source=source, fetched_at=datetime.now(timezone.utc)
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                # subscript access: the column is named "items", which shadows the
                # ColumnCollection.items() method under attribute access.
                set_={
                    "items": stmt.excluded["items"],
                    "source": stmt.excluded["source"],
                    "fetched_at": stmt.excluded["fetched_at"],
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await s.execute(stmt)
            await s.commit()
    except Exception:  # noqa: BLE001
        logger.exception("gold prices: failed to persist snapshot")


async def _load_snapshot() -> dict | None:
    """Return {items, fetched_at} from the persisted last-good row, or None."""
    try:
        async with SessionLocal() as s:
            row = await s.get(GoldPriceSnapshot, 1)
            if row and row.items:
                return {"items": row.items, "fetched_at": row.fetched_at.isoformat()}
    except Exception:  # noqa: BLE001
        logger.exception("gold prices: failed to load snapshot")
    return None


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
    if not force:
        cached = await cache_get(_CACHE_KEY)
        if cached is not None:
            return {"items": cached, "source": "tgju", "cached": True}
    try:
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
            resp = await client.get(TGJU_URL)
            resp.raise_for_status()
            current = resp.json().get("current", {})
        items = _parse(current)
        if not items:
            raise ValueError("no known symbols in TGJU payload")
        await cache_set(_CACHE_KEY, items, _TTL)
        await _save_snapshot(items)  # persist last-good so restarts survive
        return {"items": items, "source": "tgju", "cached": False}
    except Exception as e:  # noqa: BLE001 — never break the admin panel on a scrape error
        logger.warning("gold prices fetch failed: {}", e)
        cached = await cache_get(_CACHE_KEY)  # another worker may hold a fresh board
        if cached is not None:
            return {"items": cached, "source": "tgju", "cached": True, "stale": True}
        # Cold start / empty cache: fall back to the DB last-good snapshot.
        snap = await _load_snapshot()
        if snap:
            await cache_set(_CACHE_KEY, snap["items"], _TTL)  # warm the cache too
            return {
                "items": snap["items"],
                "source": "tgju",
                "cached": True,
                "stale": True,
                "fetched_at": snap["fetched_at"],
            }
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
