# pricing

Live gold/currency rate board for the storefront نرخ روز strip and the admin
pricing-reference panel. One integration (TGJU scrape) + one persisted
last-good snapshot so the board survives restarts and TGJU outages.

## Layout

| Path | What lives here |
|---|---|
| `models/gold_price_snapshot.py` | `GoldPriceSnapshot` — single row (id=1), the persisted last-good board |
| `queries/price_query.py` | `PriceQuery` — read the snapshot row (`last_board`) |
| `actions/price_action.py` | `PriceAction` — `upsert_board` (pg upsert of row id=1, owns the commit) |
| `routers/public.py` | `GET /prices` (no auth, `Cache-Control: max-age=120`) |
| `routers/admin.py` | `GET /admin/prices` (same payload, behind `require_admin`) |
| `services/tgju.py` | TGJU scraper: fetch + parse + Rial→Toman, TTL cache, stale/DB fallback, `refresh_loop` |

## Routes

Public: `GET /prices`. Admin: `GET /admin/prices`. Both return the same
`{items, source, cached, stale?, error?}` dict from `get_gold_prices()` —
it's public market data, so no separate shapes.

## Invariants & gotchas

- **Deviation from the layer table (written reason):** `services/tgju.py`
  calls `PriceAction`/`PriceQuery`, not the other way around. The scraper runs
  outside any request (app-lifespan `refresh_loop`, started in `app/main.py`),
  so there is no DI session and no router→Action path to orchestrate from; the
  service opens its own short-lived `SessionLocal()` per persistence call and
  hands it to the Action/Query. Snapshot persistence must **never raise** into
  price serving — both wrappers swallow and log.
- Toman figures from TGJU are **Rial/10**; the USD ounce (`ons`) is kept as-is
  (float). Only symbols whitelisted in `SYMBOLS` are served.
- Fallback ladder on scrape failure: shared cache (fresh from another worker,
  served `stale`) → DB snapshot (`stale`, warms the cache) → `{items: [],
  error: true}`. Never a 5xx — the panel must not break on a scrape error.
- The snapshot table holds exactly one row (id=1), upserted on every good
  scrape; `stmt.excluded["items"]` uses subscript access because the column
  name `items` shadows `ColumnCollection.items()`.
- `refresh_loop` runs **per worker** (gunicorn -w 2 => 2 scrapes/interval) —
  acceptable at current volume; gate to one worker if TGJU load ever matters.
- Cache TTL 90s vs. refresh cadence 120s: routers almost always hit cache; the
  in-process/Redis cache + refresh loop do the throttling, not the routers.

## Tests

`tests/test_gold_prices.py` (scraper unit tests, httpx + SessionLocal
monkeypatched on `services/tgju.py`), `tests/test_public_prices.py`
(public endpoint, `get_gold_prices` monkeypatched on `routers/public.py`).
