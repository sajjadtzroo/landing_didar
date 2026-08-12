# 06 — Final Report: G1–G8 (migration completed 2026-08-12)

Commits: `a18ee5d` (scaffolding) → `1e55a8d` content → `ccaba8b` pricing →
`6ffacd9` users → `1d656db` catalog → `1826dec` customers → `3a0f7d8` orders →
`b3e797b` serials(+warranty merged) → `51d4a7d` agents+dashboard → final cleanup.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| G1 | Every domain in one folder under `app/domains/<domain>/` | ✅ | 9 domains: agents, catalog, content, customers, dashboard, orders, pricing, serials (incl. warranty), users |
| G2 | No cross-domain imports of internals; public API only | ✅ | 9 per-domain `forbidden` contracts (direct deep imports banned) + composition-root exception for main.py; negative test: a deliberate deep import breaks 2 contracts |
| G3 | Zero circular imports | ✅ | `python -c "import app.main"` clean; DAG layers contract kept |
| G4 | Old layer folders gone (only `core/` + `shared/` cross-cutting) | ✅ | `app/` = main.py, seed.py, import_images.py, core/, shared/, domains/ — `api/`, `models/`, `schemas/`, `services/`, `constants/` deleted |
| G5 | Tests pass; API byte-identical | ✅ | 249 passed / 3 skipped every commit; sorted OpenAPI dump diff vs baseline **empty** at every step (tests changed only in import paths) |
| G6 | Alembic history untouched; autogenerate unchanged | ✅* | `git diff a18ee5d..HEAD -- alembic/versions` empty; `alembic check` autogenerate ops byte-identical before/after the migration. *Fresh-DB `upgrade head` fails on a PRE-EXISTING enum bug in a committed migration (finding #8) — unrelated to this refactor. |
| G7 | Git history preserved | ✅ | All moves via `git mv` (`git log --follow` works); the only splits (public.py, admin_catalog.py) note their origin in commit messages |
| G8 | Architecture contract in CI | ✅ | 11 import-linter contracts in `backend/pyproject.toml`; `.github/workflows/backend.yml` runs ruff + lint-imports + pytest (Postgres service) |

## Decisions made during execution (vs the original plan)

1. **Warranty merged into serials** — two-way dependency (passport endpoint reads
   serial+warranty+buyback; warranty routes need the serials service) = one domain
   per the spec's own merge rule.
2. **Three documented DAG exceptions** (router-level, contract-ignored):
   `orders.router_admin → serials.service` (delivery auto-mints),
   `customers.router_account → orders` (my-orders view),
   `users.router_admin_users → agents` (retailer assignment, lazy import).
3. **Routers register from main.py via direct submodule imports** — domain
   `__init__` exposes models/deps/service only; importing routers there recreated
   the deps↔models aggregation cycle. main.py is the composition root and exempt.
4. **`content_defaults` stays in `core/`** — a committed migration imports it.
5. **`service` modules are part of a domain's public API** (orders, serials) —
   callers use `from app.domains.X import service`; internals contracts allow it.

## Follow-ups (not done here, by design)

- Fix the fresh-DB enum migration bug (finding #8) — needs a migrations/ change.
- Burn down the E501 per-file-ignores (finding #9).
- Move router-level `db.commit()` into services per domain (finding #1).
- Frontend §7 mirror — descoped; revisit with ESLint `no-restricted-imports`.
