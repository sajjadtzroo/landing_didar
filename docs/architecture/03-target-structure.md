# 03 — Target Structure

```
backend/app/
  main.py                # app factory + middleware + include_router only
  core/                  # framework-level: config db security logging cache metrics limiter storage client_logs
  shared/                # cross-domain, no business rules: notifications/ constants.py
  domains/
    __init__.py          # imports every domain's models module (mapper registration + Alembic)
    <domain>/
      __init__.py        # PUBLIC API — the only legal cross-domain import surface
      router.py  schemas.py  models.py  service.py  dependencies.py  constants.py
```

## Rules (enforced by import-linter, config in backend/pyproject.toml)

1. `domains/*` may import `core/` and `shared/` — never the reverse (layers contract).
2. Cross-domain imports only via `from app.domains.<d> import X` (the `__init__` surface), never `app.domains.<d>.service` etc.
3. Domain ordering must match the DAG in 02-domain-map.md.
4. `main.py` sits above domains and may import their public APIs.

## Deliberate deviations from the spec template (no-behavior-change wins)

- **No `repository.py`** — none exists today; inventing a data-access layer is a rewrite (explicit non-goal). Queries stay in services/handlers.
- **No per-domain `tests/`** — the 32 test files stay in top-level `tests/` unchanged (G5). Optional follow-up.
- **No `exceptions.py`** — codebase idiomatically uses HTTPException.
- **Router-level commits stay** (finding 05-findings.md, not fixed in this migration).

## Alembic

`alembic/env.py` switches `from app.models import *` → `import app.domains` once the aggregator carries all models. History untouched; verified by `alembic upgrade head` on a fresh DB + empty autogenerate diff.
