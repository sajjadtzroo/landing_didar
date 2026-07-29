# Deploy to Liara

Two Docker apps + one managed PostgreSQL, all in region **iran**.
Config lives in `backend/liara.json` and `frontend/liara.json`.

App names (change in the two `liara.json` files if taken):
- backend  → `didar-gold-api`  (FastAPI, port 8000)
- frontend → `didar-gold`      (Nuxt, port 3000)
- database → `didar-gold-db`   (PostgreSQL)

The backend entrypoint runs `alembic upgrade head` + idempotent seed on every boot,
so the schema and starter data appear automatically on first deploy.

---

## 0. Log in (interactive — run yourself)

```
liara login          # authenticate the info@didargold.ir account
liara account:list   # confirm it's the current 👍 account (or: liara account:use <name>)
```

## 1. Create the PostgreSQL database

```
liara db:create --name didar-gold-db --type postgres --version 16 --plan <plan>
```
Then grab its connection string:
```
liara db:info didar-gold-db
```
Copy the connection URL and **change the scheme** to asyncpg:
`postgresql://…`  →  `postgresql+asyncpg://…`

## 2. Create the two apps

```
liara app:create --name didar-gold-api --platform docker
liara app:create --name didar-gold     --platform docker
```

## 3. Set backend env vars

```
liara env:set --app didar-gold-api \
  DATABASE_URL="postgresql+asyncpg://<user>:<pass>@<host>:<port>/<db>" \
  FRONTEND_ORIGIN="https://didar-gold.liara.run" \
  ADMIN_ORDER_BASE_URL="https://didar-gold.liara.run/admin/orders" \
  SECRET_KEY="7ZlVnGpo6VA_bGqikwtaaThkPZiDm3lqScRgvm7rf7Gw0JoBlA7UxS_ilfCSbOnf" \
  ADMIN_USERNAME="admin" \
  ADMIN_PASSWORD_HASH="<bcrypt-hash>"
```
Generate the admin bcrypt hash (never ship a plaintext prod password):
```
docker compose run --rm backend python -c \
  "from app.core.security import hash_password; print(hash_password('YOUR_STRONG_PASSWORD'))"
```

## 4. Set frontend env vars  (⇦ Matomo wired here)

```
liara env:set --app didar-gold \
  NUXT_PUBLIC_API_BASE="https://didar-gold-api.liara.run/api/v1" \
  NUXT_API_BASE_INTERNAL="https://didar-gold-api.liara.run/api/v1" \
  NUXT_PUBLIC_MATOMO_URL="https://<YOUR-MATOMO-DOMAIN>/" \
  NUXT_PUBLIC_MATOMO_SITE_ID="<YOUR-SITE-ID>" \
  NUXT_PUBLIC_MATOMO_GOAL_ORDER="1" \
  NUXT_PUBLIC_MATOMO_GOAL_PHONE="2" \
  NUXT_PUBLIC_MATOMO_DIM_PROVINCE="1" \
  NUXT_PUBLIC_MATOMO_DIM_SOURCE="2"
```
> The Goal / Dimension IDs must match what you create in the Matomo UI
> (Goals: order-submit, phone-click; Custom Dimensions: province, utm_source).
> In Matomo → Administration → Websites, add `didar-gold.liara.run` to the site's
> allowed URLs so tracking isn't rejected.

## 5. Deploy

```
liara deploy --path backend  --app didar-gold-api
liara deploy --path frontend --app didar-gold
```

## 6. Verify

```
curl -s -o /dev/null -w "%{http_code}\n" https://didar-gold-api.liara.run/health
curl -sL https://didar-gold.liara.run/ | grep -o 'درخشش طلای'          # landing renders
```
- Open the site, submit a test order → Matomo → Visitors → Visit Log shows the
  page view, the `order-submit` goal, and province/source custom dimensions.
