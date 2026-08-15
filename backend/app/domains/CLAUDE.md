# Backend Architecture — Modular Monolith + CQRS-light

Auto-loaded when working under `app/domains/`. This is the contract every
domain follows; deviations need a written reason in the domain's README.md.

## Canonical domain skeleton

Every domain uses the same folders — even when a folder holds a single file:

```
app/domains/{domain}/
├── __init__.py     # PUBLIC API — the only surface other domains may import
├── README.md       # purpose, routes, invariants, gotchas
├── models/         # SQLAlchemy models (one file per aggregate)
├── schemas/        # Pydantic DTOs — request/response shapes (server is truth)
├── queries/        # read side:  {Entity}Query      — SELECT only
├── actions/        # write side: {Entity}Action / {Verb}{Entity}Action — owns commit
├── routers/        # thin HTTP layer: public.py, admin.py, ...
└── services/       # optional: stateless integrations (SMS, storage, realtime)
```

Base classes live in `app/shared/cqrs.py` (`BaseQuery`, `BaseAction`,
`MAX_PAGE_SIZE`). `app/shared/` is this codebase's "Common" module.

## Layer access table (the heart of the convention)

| Layer      | May use                                                            | Never |
|------------|--------------------------------------------------------------------|-------|
| **router** | Query, Action, schemas, FastAPI deps (`require_admin`, limiter)    | `select()`, `db.commit()`, business rules |
| **Action** | models, Query, services, other domains' `__init__` public API      | HTTP response shaping |
| **Query**  | models (read-only)                                                 | flush/commit, mutation of any row |
| **service**| external I/O (HTTP, SMS, MinIO, Redis pub/sub) via `app.core`/`app.shared` | holding per-request state |
| **schemas**| pydantic only                                                      | importing models or the session |

- Routers stay thin: parse/validate → call one Query or Action method → return
  DTO. If a handler needs an `if` about domain state, that `if` belongs in an
  Action/Query.
- **The commit boundary lives in Actions.** `await db.commit()` appears only
  inside `actions/` (and `app/main.py` middleware). Deliberate second commits
  (e.g. "never roll back the order because a side record failed") are fine —
  inside the Action, with a comment.
- Queries always start from `self.stmt()` — never cache statements or results
  on the instance.
- Cross-domain access goes through the other domain's `__init__.py` public
  API. `lint-imports` (11 contracts in `pyproject.toml`) enforces this and the
  domain DAG in CI — run it before pushing.

## Naming

| Thing            | Pattern                              | Example |
|------------------|--------------------------------------|---------|
| Read class       | `{Entity}Query` in `queries/{entity}_query.py` | `OrderQuery` |
| CRUD write class | `{Entity}Action` in `actions/{entity}_action.py` | `ProductAction` |
| Business command | `{Verb}{Entity}Action`, single `execute()`-style method | `CreateOrderAction` |
| DTO              | `{Entity}Create / {Entity}Update / {Entity}Out` | `OrderCreate` |
| Router file      | `routers/{audience}.py` (`public`, `admin`, `account`, `ws`) | `routers/admin.py` |

Files are snake_case; one main class per file; packages re-export via
`__init__.py` so import paths stay short.

## Two domain archetypes

- **CRUD/domain** (catalog, orders, content, …): models + schemas + queries +
  actions + routers.
- **Integration-heavy** (chat realtime, catalog MinIO import, order SMS):
  the external-facing part is a stateless `services/` helper behind a small
  interface; the Action orchestrates it. Provider choice comes from config —
  never `if provider == ...` chains in routers.

## Wiring & traps (load-bearing, learned the hard way)

- `app/main.py` is the composition root; **router registration order matters**
  (`orders` public router must precede `catalog`'s so
  `/products/best-sellers` isn't swallowed by `/products/{slug}`).
- `app/core/content_defaults.py` **cannot move** — Alembic migration `0007`
  imports it.
- `app/domains/__init__.py` imports every domain so `Base.metadata` sees all
  tables (Alembic autogenerate + tests depend on it).
- OpenAPI is a frozen contract: `docs/architecture/openapi-baseline.json`.
  After any router change run
  `python scripts/dump_openapi.py` (with `PYTHONPATH=.`) and diff — refactors
  must produce a byte-identical schema.
- Octane-style statelessness applies here too: Query/Action instances are
  per-request; module-level mutable state is forbidden (workers are long-lived).

## Testing

- Every feature (route or Action) has a feature test under
  `tests/{domain}/`, mirroring this tree. Fixtures: `tests/conftest.py`
  (`client`, `admin_client`, `approved_client`, real Postgres, TRUNCATE per test).
- Verification loop before every commit:
  `ruff check app` → `lint-imports` → `pytest -q` → OpenAPI diff.

## Anti-patterns (reject in review)

- `select()` or `db.commit()` in a router.
- Business logic in a router or a schema validator that touches the DB.
- Deep import into another domain (`app.domains.x.models` from outside `x`).
- A Query method that writes; an Action method that shapes HTTP responses.
- New module-level mutable state.
