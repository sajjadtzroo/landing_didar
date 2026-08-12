# 01 — Current State (captured 2026-08-12, pre-migration)

Backend `backend/app/`, ~6,500 LOC, **layer-first**:

| Layer | Files | LOC | Notes |
|---|---|---|---|
| `api/v1/` | 18 routers | 2,522 | 97 routes; role-oriented split (admin_*, agent, public, account, auth) |
| `api/` | deps.py, limiter.py | 129 | auth Depends resolvers + slowapi limiter |
| `services/` | 8 (+notifications/) | 1,023 | gold_prices, orders, serials, product_import, minio_import, sms, storage |
| `models/` | 13 | 799 | SQLAlchemy 2.0 async, 20 tables |
| `schemas/` | 13 | 768 | Pydantic DTOs |
| `core/` | 8 | 714 | config, db, security, logging, cache, metrics, content_defaults |
| `constants/` | provinces.py | 34 | |
| root | main.py (328), seed.py | 513 | app factory + middleware + router registration |

Key facts (evidence gathered read-only):

- **Zero circular imports.** Direction is already clean: `api → services → models`, everything → `core` (G3 pre-satisfied).
- **God file:** `api/v1/public.py` (523 LOC) mixes catalog, content, pricing, orders, serials, warranty routes.
- **Most-imported internal modules** (shared kernel): `core.db`, `api.deps`, `models/__init__`, `core.config`, `core.logging`, `core.cache`, `core.security`.
- **Models & FKs:** see 02-domain-map.md — FK edges are the domain-boundary signal.
- **Commits inside routers:** ~40 `db.commit()` calls in endpoint handlers (account ×8, admin_catalog ×9, agent ×4, …) + audit middleware commit at `main.py:127`. Recorded as a finding (05), NOT fixed here (non-goal).
- **Alembic:** `alembic/env.py` imports `Base` from `app.core.db` and `from app.models import *`; `target_metadata = Base.metadata`.
- **Tests:** 32 files in top-level `tests/`, run against real Postgres (:5434). Baseline: **249 passed, 3 skipped**.
- **Ruff baseline is NOT clean:** 66 pre-existing violations (45×E501, 10×I001, 8×B904, 2×UP017, 1×F401). Per-PR gate is therefore "no NEW violations", not "clean".
- **OpenAPI baseline:** `docs/architecture/openapi-baseline.json` (sorted-keys dump via `backend/scripts/dump_openapi.py`).
