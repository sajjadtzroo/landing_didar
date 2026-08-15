# customers

Phone-OTP customer accounts for the shop: login, profile, verification
documents, wishlist (favorites), addresses, and the admin verification panel.
Follows the canonical skeleton in `../CLAUDE.md` (reference: `../orders/`).

## Layout

| Path | What lives here |
|---|---|
| `models/customer.py` | `Customer`, `CustomerAddress`, `Favorite`, `OtpCode`, `CustomerVerificationStatus` |
| `schemas/customer.py` | OTP / profile / address / verification DTOs |
| `queries/customer_query.py` | `CustomerQuery` — session customer (401), admin list, orders-by-phone |
| `queries/address_query.py` | `AddressQuery` — list + ownership-checked lookup |
| `queries/favorite_query.py` | `FavoriteQuery` — wishlist as live catalog products |
| `actions/request_otp_action.py` | `RequestOtpAction` — mint + store hashed code, SMS or reveal |
| `actions/verify_otp_action.py` | `VerifyOtpAction` — code check, attempt burning, get-or-create customer |
| `actions/customer_action.py` | `CustomerAction` — profile update, verification document add/remove |
| `actions/verify_customer_action.py` | `VerifyCustomerAction` — admin approve/reject + notification SMS |
| `actions/address_action.py` | `AddressAction` — CRUD with single-default invariant |
| `actions/favorite_action.py` | `FavoriteAction` — idempotent add / remove |
| `routers/account.py` | `/account/*` — OTP login, me, documents, orders, favorites, addresses |
| `routers/admin.py` | `/admin/customers*` — list/detail/verification decision |
| `dependencies.py` | customer-session Depends (`require_customer`, `optional_customer`) — FastAPI wiring, stays at domain root |

## Routes

Account: `POST /account/otp/request` (rate-limited 5/h/IP), `POST
/account/otp/verify`, `POST /account/logout`, `GET/PATCH /account/me`,
`POST /account/me/documents`, `DELETE /account/me/documents/{idx}`,
`GET /account/me/orders`, `GET/PUT/DELETE /account/me/favorites*`,
`GET/POST/PATCH/DELETE /account/me/addresses*`.
Admin: `GET /admin/customers`, `GET /admin/customers/{id}`,
`PATCH /admin/customers/{id}/verification`.

## Invariants & gotchas

- **Identity is the phone.** Orders are linked by matching phone, not an FK —
  purchases made before signup appear in `/me/orders`; guest checkout
  auto-registers a `Customer` (in orders' `CreateOrderAction.checkout`).
- OTP codes are **hashed at rest**; verify reads the newest unconsumed row,
  a wrong guess commits `attempts += 1` (survives the 400), 5 wrong tries kill
  the code, TTL 300 s. `dev_code` is returned outside production — and for
  allowlisted `otp_test_phones` even in production (which also skip real SMS).
- `verification_documents` is JSONB — always **reassign** the list (never
  append in place) so SQLAlchemy flags the change. An upload from
  unverified/rejected flips status back to `pending`; deleting a document is
  only allowed while `pending`.
- Admin verification decision: same status twice is a no-op that must **not**
  re-send SMS.
- Addresses: at most one default (`AddressAction._clear_default` first);
  someone else's address id is a **404**, never a 403.
- `orders`' public API imports `Customer`, so `CustomerQuery.orders_for`
  imports `Order` **lazily** (module-scope would make `customers.__init__`
  circular). Both orders imports here are DAG exceptions in `pyproject.toml`.
- Admin list pages manually with a 500 default — deliberately **not** capped by
  `MAX_PAGE_SIZE` (the admin UI is un-paginated for now).
- `dependencies.py` is not business logic; it stays at the domain root and is
  exported via the public API only (deep import is forbidden by lint-imports).

## Tests

`tests/test_account.py`, `tests/test_admin_customers.py`; the
`approved_client` fixture in `tests/conftest.py` logs in through the real OTP
flow. SMS spies patch `actions/request_otp_action.py` /
`actions/verify_customer_action.py` (where `send_sms` is looked up).
