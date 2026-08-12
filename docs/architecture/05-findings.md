# 05 — Findings (observed during migration; intentionally NOT fixed here)

1. **Commits in routers.** ~40 `await db.commit()` calls live in endpoint handlers
   (account.py ×8, admin_catalog.py ×9, agent.py ×4, admin_landings ×3, …) rather than
   in services. Consistent pattern, works, but transaction scope is per-handler.
   Upgrade path: move mutations behind service functions per domain.
2. **Audit middleware commits its own session** (`main.py` audit middleware) — separate
   transaction from the request handler; an audit row can persist for a failed request
   (or vice versa). Acceptable for an audit trail; documented so it's a choice, not a surprise.
3. **Ruff baseline not clean:** 66 pre-existing violations (45×E501, 10×I001, 8×B904,
   2×UP017, 1×F401). Left untouched to keep refactor commits pure moves.
4. **Pagination is hand-rolled per endpoint** (offset/limit + count). Fine at this scale;
   a shared helper would remove ~10 small duplications.
5. **`public.py` and `admin_catalog.py` each span multiple domains** — split during
   migration (the only non-`git mv` operations; noted in their commit messages).
