# Didar Gold — Mobile Landing + Order Panel

Mobile-first lead-capture site for **Didar Gold**, a wholesale gold-jewelry
supplier. A retailer browses 10 products, adds a few to a cart, submits their
contact details, and the sales team is notified by **SMS** to call back. Includes
a lightweight admin panel and Matomo analytics. **No payment gateway** — this is
an order/lead-request flow.

- **Frontend:** Nuxt 3 (Vue 3, `<script setup>`, TypeScript, Tailwind), SSR on
  for the landing page, `/admin` client-only. Persian / RTL.
- **Backend:** FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, PostgreSQL 16.
- **Analytics:** Matomo only (no Google anything).

```
/frontend   Nuxt app     — domain-grouped; conventions in frontend/README.md
/backend    FastAPI app  — modular monolith; conventions in backend/app/domains/CLAUDE.md
docker-compose.yml
```

## Quick start (Docker)

```bash
docker compose up --build
```

Brings up Postgres + FastAPI + Nuxt. The backend entrypoint **waits for the DB,
runs Alembic migrations, then seeds** 10 products + 8 FAQs (idempotent).

- Landing: <http://localhost:3000>
- Admin:   <http://localhost:3000/admin>  (login **admin / admin123** by default)
- API:     <http://localhost:8000/api/v1>  · docs <http://localhost:8000/docs>

The dev admin password is hashed at container boot from `ADMIN_PASSWORD`
(default `admin123`). Override with your own `.env` at the repo root:

```env
ADMIN_PASSWORD=your-strong-password       # dev bootstrap (hashed at boot)
SECRET_KEY=some-long-random-string
MATOMO_URL=https://analytics.didargold.com
MATOMO_SITE_ID=1
```

## Local dev (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # then edit
# generate an admin password hash:
python -m app.core.security "your-password"   # paste into ADMIN_PASSWORD_HASH
alembic upgrade head                       # migrations
python -m app.seed                         # seed 10 products + 8 FAQs
uvicorn app.main:app --reload
# tests + lint
pytest && ruff check .
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env                       # then edit
npm run dev
```

## How things fit together

- **Orders** copy product name + price at order time into `order_items` — historical
  orders never change when live prices move. Prices are server-trusted (the client
  only sends product IDs + quantities).
- **Idempotency:** the form generates a UUID on open and sends it as
  `Idempotency-Key`; a repeated key returns the original order (double-tap safe).
- **Anti-spam:** a hidden honeypot field + `slowapi` rate limit (5 orders / IP / hour).
- **Validation** is defined once as Zod on the client (`utils/orderSchema.ts`) and
  mirrored in Pydantic on the server (`schemas/order.py`) — the server is the truth.
  Phone is validated as an Iranian mobile (`^09\d{9}$`).

## Admin notification (SMS is primary)

`backend/app/services/notifications/` holds a `NotificationAdapter` protocol with:

- **`SmsAdapter`** — primary. Kavenegar-style HTTP by default; set `SMS_API_KEY`,
  `SMS_SENDER`, `SMS_ADMIN_PHONE`. With no key set it falls back to `LogSmsAdapter`
  (prints the message) so dev/tests never fail on a real send.
- **`TelegramAdapter`**, **`EmailAdapter`** — stubs behind the same protocol.

**To swap the channel**, edit `get_adapter()` in
`services/notifications/__init__.py` to return a different adapter. Notifications
dispatch via `BackgroundTasks` **after commit**, retry once, and never block or
roll back the order (the admin unread badge is the backstop).

**To swap the SMS provider**, edit the URL/params in `SmsAdapter.send_new_order`.

## Media storage

Uploaded product images go to `backend/media` via `LocalStorage` (`services/storage.py`),
served at `/media`. Swap `get_storage()` for an S3 implementation in production —
the `Storage` protocol keeps callers unchanged.

## Matomo setup

1. Set `NUXT_PUBLIC_MATOMO_URL` and `NUXT_PUBLIC_MATOMO_SITE_ID` (frontend env).
   Blank ⇒ tracker is disabled (dev).
2. In the Matomo UI, **enable Ecommerce** for the site (abandoned-cart data shows
   under *Ecommerce → Overview* — likely the most useful report here).
3. Create these and put their IDs in the frontend env:
   - **Goal 1 — Order submitted** → `NUXT_PUBLIC_MATOMO_GOAL_ORDER`
   - **Goal 2 — Phone click** → `NUXT_PUBLIC_MATOMO_GOAL_PHONE`
   - **Custom Dimension (visit) — Province** → `NUXT_PUBLIC_MATOMO_DIM_PROVINCE`
   - **Custom Dimension (visit) — Traffic source** → `NUXT_PUBLIC_MATOMO_DIM_SOURCE`
4. Tracking is loaded in `plugins/matomo.client.ts`, which also tracks **every SPA
   route change** (the default snippet only fires once). All `_paq` access goes
   through `composables/useAnalytics.ts` — no component touches it directly.

Self-hosting Matomo with anonymized IPs + cookieless config avoids a consent
banner. On Matomo Cloud, gate the tracker behind a notice with
`requireCookieConsent` / `rememberCookieConsentGiven`.

Attribution (UTM + referrer) is also captured to `sessionStorage` on landing,
sent with the order, and stored on the row — so sales keeps the source even if
the tracker was blocked (`plugins/attribution.client.ts`).

## Design system

Tokens from `DESIGN_SYSTEM copy.md` (luxury gold `#B08A57` / navy `#041E42` /
cream, sharp corners, Doran font, ✦ gold-hairline divider) are mapped in
`frontend/tailwind.config.ts` + `frontend/assets/css/main.css`. Text gold uses the
accessible `gold-text` token; raw `gold` is decorative only.

**Fonts:** Doran woff2 files are **not** in the repo — drop
`Doran-{Light,Regular,Medium,Bold}.woff2` into `frontend/public/fonts/`. Until
then it falls back to Vazirmatn / system-ui. Hero/product images are placeholders
(`placehold.co`); replace with real assets in `public/media/` and the seed.

---

## Closing note

### Tokens I had to add
- **Semantic status tokens** (`danger/success/warning` + `-soft`) as CSS vars per
  theme — the design doc listed the hex pairs but not var names; named them to
  match the existing `--surface`/`--ink` convention.
- **Hero overlay gradient** (`from-navy-deep/85 via-navy/45`) and the **translucent
  sticky-header** blur — derived from existing `navy`/`header` tokens, not new hues.
- **`--font-family` fallback** `Vazirmatn` before `system-ui` (doc names Doran +
  Vazirmatn as the Persian pairing).
- Radius stays at the brand's 0 (sharp); only `rounded-full` survives.

### Assumptions
- **SMS provider = Kavenegar-style HTTP** (common in Iran). Adapter is one edit
  away from any other provider.
- **Language = Persian/RTL** with English `value`s for provinces so the server
  contract stays stable; the design system was already RTL-first.
- Prices are **Toman**, whole numbers (no decimals) — matches `Numeric(_, 0)`.
- Single admin account (no user table), per the brief.
- Dev admin `admin/admin123`; **change before any real deploy.**

### Recommendations
- **Reorder UX:** products/FAQs reorder via keyboard-accessible up/down arrows
  rather than mouse-only drag — more accessible and less code. Add HTML5 drag only
  if the client specifically wants it.
- **Rate-limit store:** `slowapi` uses in-memory counters — fine for one process,
  but move to Redis if you run multiple gunicorn workers/replicas so the 5/hour
  limit is shared.
- **Idempotency key TTL:** keys live forever on the row today; add a cleanup job if
  volume grows.
- Add real **Doran fonts + product photography** before measuring Lighthouse — the
  placeholders will skew LCP/CLS.
- Consider a **theme toggle** (dark tokens already exist) if the brand wants the
  night palette on the storefront.
