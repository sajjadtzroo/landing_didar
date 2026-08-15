# serials

Per-piece authenticity codes (the "passport"), public verification with scan
logging, QR labels, warranty activation (WO 7.8) and buyback requests
(WO 7.9). Warranty/buyback live here because they are serial-lifecycle
events — the passport endpoint reads all three.

## Layout

| Path | What lives here |
|---|---|
| `models/serial.py` | `ProductSerial`, `ProductSerialStatus`, `SerialEvent`, `SerialScan` |
| `models/warranty.py` | `Warranty`, `BuybackRequest`, `BuybackStatus` |
| `schemas/serial.py` | verify/passport + admin serial DTOs |
| `schemas/warranty.py` | warranty activation + buyback DTOs |
| `queries/serial_query.py` | `SerialQuery` — code lookups (normalized), passport events, admin list/export with scan aggregate |
| `queries/warranty_query.py` | `WarrantyQuery` — by-serial lookup, passport warranty state |
| `queries/buyback_query.py` | `BuybackQuery` — latest/open request checks, admin list/export |
| `actions/serial_action.py` | `SerialAction` — batch + per-order minting, lifecycle events, scan log, admin patch |
| `actions/warranty_action.py` | `ActivateWarrantyAction` — sold + warrantable + not-yet-activated, race-safe |
| `actions/buyback_action.py` | `BuybackAction` — public request (one open per piece), admin review |
| `routers/public.py` | verify, QR label, warranty activation, buyback request |
| `routers/admin.py` | admin serial list/generate/export/patch/delete |
| `routers/admin_buybacks.py` | admin buyback list/patch/export |
| `services/codes.py` | pure code helpers: `new_code`, `normalize`, `format_code`, `qr_png` |

## Routes

Public (all rate-limited): `GET /serials/verify`, `GET /serials/{code}/qr.png`,
`POST /serials/{code}/warranty`, `POST /serials/{code}/buyback`.
Admin: `GET/POST/PATCH/DELETE /admin/serials*`, `GET /admin/serials/export`,
`GET/PATCH /admin/buybacks*`, `GET /admin/buybacks/export` (CSV).

## Invariants & gotchas

- Codes are stored **canonical** (uppercase, no separator, `DGVAB12CD34`) and
  rendered `DGV-AB12CD34`; every lookup normalizes first (`services/codes.py`).
- Serial rows **snapshot** product name/karat/weight/image at generation time —
  a certificate describes what was actually sold, even after the product row
  changes. `products.id` FK is RESTRICT for the same reason.
- Generation inserts with `ON CONFLICT DO NOTHING` on the unique code index and
  re-codes only the shortfall — correct under concurrent batches.
- `SerialAction.generate_for_order(order)` is **idempotent per order and does
  NOT commit** — the caller's transaction owns it. Called by orders'
  `OrderAction` (lazy import, cycle: serials' public API imports orders) and
  agents' `AgentOrderAction`.
- Unknown and revoked codes return the SAME opaque 404 on every public route —
  a revoked code is not authentic and codes can't be enumerated.
- `verify` deliberately commits inside a GET: every hit lands in `serial_scans`
  (the copy-attack signal: verify_count / first_verified_at in the admin list).
- Mint is not stored as an event — a serial's `created_at` *is* the mint;
  public timeline = minted + (`sold`, `warranty_activated`, `buyback_requested`).
  A patch back to `in_stock` logs as `restored`.
- Warranty: one per piece (unique serial_id), 12 months from activation, status
  derived from `expires_at`. Buyback: one *open* request per piece, enforced by
  a partial unique index — both handle the IntegrityError race as 409.
- Agents' `GalleryAction.quick_sell` row-locks `ProductSerial`
  (`with_for_update`) via the public model export — keep `ProductSerial`
  exported.

## Tests

`tests/test_serials.py`, `tests/test_warranty_buyback.py`, plus delivery
minting coverage in `tests/test_admin_orders.py` / agents tests.
