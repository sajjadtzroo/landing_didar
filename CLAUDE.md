# Didar Gold — CLAUDE.md (entry point)

Mobile-first, Persian/RTL lead-capture platform for a **wholesale gold-jewelry
supplier**: retailers browse products → cart → submit contact details → sales
follows up (SMS). **No payment gateway.** Order totals are **grams**, not Toman.

## Stack

- **Backend** `backend/`: FastAPI 0.115 · SQLAlchemy 2 async + asyncpg ·
  Alembic · Pydantic 2 · Python 3.12 · slowapi · loguru · Redis · MinIO
- **Frontend** `frontend/`: Nuxt 3 · Vue 3 · Pinia · Tailwind · Zod +
  vee-validate (server mirrors the Zod rules — server is truth)
- **Infra**: Docker Compose · Caddy (auto-TLS) on a VPS · Postgres 16 ·
  observability stack (Loki/Grafana/Prometheus) in `observability/`

## Architecture — Modular Monolith + CQRS-light

`backend/app/domains/{domain}/` with the canonical skeleton
`models/ schemas/ queries/ actions/ routers/ services/`.
**The contract lives in `backend/app/domains/CLAUDE.md`** (auto-loads there);
reference implementation: `backend/app/domains/orders/`.
Import rules are CI-enforced by import-linter (`backend/pyproject.toml`).

## Dev commands

```bash
docker compose up -d db redis            # deps only (host dev)
docker compose up -d                     # full stack: api :8001, front :3001
# Tests/lint run in a python:3.12 container or venv (host python may be 3.9):
cd backend && ruff check app && lint-imports && pytest -q
python scripts/dump_openapi.py           # PYTHONPATH=. — diff vs docs/architecture/openapi-baseline.json
```

Test DB: real Postgres on :5434 (`didar_test`), schema via create_all,
TRUNCATE per test. CI also runs `alembic upgrade head` on a fresh DB.

## Non-negotiables

1. Routers contain no `select()` and no `db.commit()` — Query/Action classes
   only (see the layer table in `backend/app/domains/CLAUDE.md`).
2. Cross-domain imports only via the other domain's `__init__` public API.
3. OpenAPI baseline diff must stay empty for refactors; API changes update
   `docs/architecture/openapi-baseline.json` deliberately in the same commit.
4. Router registration order in `app/main.py` is load-bearing (orders before
   catalog); `app/core/content_defaults.py` must not move (migration 0007).
5. Every backend feature ships with a feature test; every domain has a
   README.md kept current (doc-sync table in `docs/architecture/README.md`).
6. Persian copy stays in Persian; money/weights: integer RIAL is legacy —
   orders are measured in grams.

## Docs map

| Doc | What's in it |
|---|---|
| `backend/app/domains/CLAUDE.md` | architecture contract (layer table, naming, skeleton) |
| `backend/app/domains/{domain}/README.md` | per-domain purpose, routes, invariants |
| `docs/architecture/` | domain map, migration history, findings, OpenAPI baseline |
| `docs/deploy-vps.md` | production deploy (VPS + Compose + Caddy) — **the** deploy doc |
| `DEPLOY.md` | DEPRECATED Liara path (teardown reference only) |
| `docs/analytics-matomo.md` | Matomo wiring |
| `observability/README.md` | logs/metrics/dashboards/alerting + X-Request-ID contract |
| `docs/perf/` | load-test reports & capacity math |
