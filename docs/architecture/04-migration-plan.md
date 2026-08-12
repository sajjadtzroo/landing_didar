# 04 — Migration Plan (one domain per commit, lowest-dependency first)

| # | Commit | Contents | Rollback |
|---|---|---|---|
| 0 | scaffolding | OpenAPI baseline, import-linter, `domains/` + `shared/` packages, these docs | revert commit |
| 1 | content | Landing/Portfolio/FAQ models+schemas+routers; split FAQ out of admin_catalog, content routes out of public.py; content_defaults | revert commit |
| 2 | pricing | gold_price model, gold_prices service + refresh loop, admin_prices, public /prices | revert commit |
| 3 | users | user model, auth/admin_users/admin_audit routers, auth resolvers from api/deps.py (shim left, `# DEPRECATED: remove in step 10`) | revert commit |
| 4 | catalog | product+import_job models, products slice of admin_catalog, catalog slice of public.py, import services | revert commit |
| 5 | customers | customer models, account, admin_customers | revert commit |
| 6 | orders | order models, orders service, admin_orders, public /orders* | revert commit |
| 7 | serials | serial models, serials service, admin_serials, public serial routes | revert commit |
| 8 | warranty | warranty models, admin_buybacks, public warranty/buyback routes | revert commit |
| 9 | agents + dashboard | agent models/routers, admin_stats | revert commit |
| 10 | cleanup | delete shims + legacy folders, full import-linter DAG + internals contracts, CI wiring, final G1–G8 report | revert commit |

## Per-commit verification loop

1. `git mv` (G7) → fix imports (shims only where still referenced).
2. `.venv/bin/ruff check app` — **no new violations** vs baseline (66).
3. `.venv/bin/python -m pytest -q` — 249 passed, 3 skipped.
4. `.venv/bin/lint-imports` — contracts kept.
5. `PYTHONPATH=. .venv/bin/python scripts/dump_openapi.py | diff - ../docs/architecture/openapi-baseline.json` — **empty** (G5).
6. Commit `refactor(<domain>): move to domain package — no behavior change`.

Docker boot + smoke test at step 10 (final) and at any step touching main.py wiring.
