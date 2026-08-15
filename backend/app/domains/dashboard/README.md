# dashboard

Read-only KPI aggregation for the admin panel. Sits high in the domain DAG:
it reads other domains' data (orders today) via their public APIs and owns no
tables of its own.

## Layout

| Path | What lives here |
|---|---|
| `queries/dashboard_query.py` | `DashboardQuery` — all admin-stats aggregations (counts, conversion, 14-day series, top products, provinces) |
| `routers/admin.py` | `GET /admin/stats` — thin wrapper over `DashboardQuery.stats()` |

No `models/`, `schemas/`, or `actions/`: the domain is a pure read side over
other domains' models, so there is nothing to persist, no DTO contract beyond
the stats dict, and no write commands. If a mutation ever lands here, it gets
an `actions/` package per `../CLAUDE.md`.

## Routes

Admin: `GET /admin/stats` (requires admin; registered in `app/main.py` under
`tags=["admin:stats"]`).

## Invariants & gotchas

- **`total_value` is GRAMS, not Toman** — orders quantify wholesale gold by
  weight (see orders domain README).
- `orders_by_day` (last 14 days) and `by_status` are **zero-filled** so charts
  render continuous lines / all statuses; don't "simplify" that away.
- `conversion_rate` counts `confirmed` + `shipped` over all orders, rounded
  to 3 decimals; 0 when there are no orders.
- Cross-domain reads must go through the source domain's `__init__` public API
  (`from app.domains.orders import Order, ...`) — dashboard is above orders in
  the DAG, so a plain module-scope import is fine (no cycle, no lazy import).
- `DashboardQuery` uses `model = Order` (the primary aggregate it reads);
  aggregations over other domains get their own named readers on the same
  class.

## Tests

`tests/test_admin_stats.py` (HTTP-level; auth, empty-DB shape, populated
stats).
