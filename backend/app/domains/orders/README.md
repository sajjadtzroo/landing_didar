# orders

Checkout, account-less tracking, admin order management, and new-order SMS
alerts for the wholesale gold flow. This domain is the **reference
implementation** of the canonical skeleton in `../CLAUDE.md`.

## Layout

| Path | What lives here |
|---|---|
| `models/order.py` | `Order`, `OrderItem`, `OrderStatusLog`, `OrderStatus`, `ContactMethod` |
| `schemas/order.py` | Zod-mirror DTOs — server is the source of truth |
| `queries/order_query.py` | `OrderQuery` — admin list/filter/sort/export, tracking lookups, best-sellers |
| `actions/create_order_action.py` | `CreateOrderAction` — core create (`execute`) + guest checkout flow (`checkout`) |
| `actions/order_action.py` | `OrderAction` — admin update, status log, serial minting on delivery |
| `routers/public.py` | checkout + `/orders/track` + `/products/best-sellers` |
| `routers/admin.py` | admin list/export/detail/patch/generate-serials |
| `services/notifications/` | SMS adapter (PayamSMS) with log fallback for dev/tests |

## Routes

Public: `POST /orders` (rate-limited 5/h/IP), `GET /orders/track`,
`GET /products/best-sellers`. Admin: `GET/PATCH /admin/orders*`,
`GET /admin/orders/export` (CSV), `POST /admin/orders/{id}/generate-serials`.

## Invariants & gotchas

- **Totals are GRAMS**, not Toman — wholesale gold is quantified by weight.
  `OrderItem.unit_price` is legacy, no longer populated.
- Line items **snapshot** product name/weight at order time; never join live.
- `Idempotency-Key`: pre-checked in the router (repeat = same response, no
  re-notify); a same-key race inside `CreateOrderAction.execute` returns the
  winning row instead of 500-ing.
- Honeypot field `website` → fake `DG-000000` success, nothing persisted.
- Guest checkout auto-registers a `Customer` (identity = phone) in a
  **separate commit** — a failure there must never roll back the order.
- `status=delivered` stamps `delivered_at` once and mints one authenticity
  serial per piece (idempotent; serials domain, lazy-imported to avoid a
  cycle — see comment in `actions/order_action.py`).
- The public router must be registered **before** catalog's in `app/main.py`
  (`/products/best-sellers` vs `/products/{slug}`).
- New-order SMS runs as a background task after commit; `_notify` retries once
  and never raises into the request.

## Tests

`tests/test_orders.py`, `tests/test_orders_service.py`,
`tests/test_admin_orders.py`, `tests/test_best_sellers.py`,
`tests/test_notifications.py`, plus checkout coverage in `tests/test_public.py`.
