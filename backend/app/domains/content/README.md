# content

Admin-curated marketing content: landing pages, portfolios (curated /shop
sections) and FAQs, plus their cached public read side. Follows the canonical
skeleton in `../CLAUDE.md`.

## Layout

| Path | What lives here |
|---|---|
| `models/landing.py` `models/portfolio.py` `models/faq.py` | `Landing`, `Portfolio`, `FAQ` |
| `schemas/` | DTOs per aggregate; `LandingGroupOut` is shared by landings AND portfolios |
| `queries/landing_query.py` | `LandingQuery` — by-slug read, admin list, slug uniqueness |
| `queries/portfolio_query.py` | `PortfolioQuery` — active-only public reads, admin list, slug uniqueness |
| `queries/faq_query.py` | `FaqQuery` — active-ordered public list, admin list |
| `queries/product_groups.py` | `resolve_groups()` — group→product resolution against the live catalog, shared by the landing and portfolio queries |
| `actions/landing_action.py` | `LandingAction` — create (409 on slug clash), update/delete + cache bust |
| `actions/portfolio_action.py` | `PortfolioAction` — create/update/delete with slug-clash 409s + list/detail cache busts |
| `actions/faq_action.py` | `FaqAction` — plain CRUD |
| `routers/public.py` | cached public reads: landings, portfolios, FAQs |
| `routers/admin_faqs.py` `routers/admin_landings.py` `routers/admin_portfolios.py` | admin CRUD |
| `services/cache.py` | stateless cache-bust helpers over `app.core.cache` |

## Routes

Public: `GET /landings/{slug}`, `GET /portfolios`, `GET /portfolios/{slug}`,
`GET /faqs`. Admin: `GET/POST/PATCH/DELETE /admin/faqs*` (tags
`admin:catalog` — historical), `/admin/landings*` (`admin:landings`),
`/admin/portfolios*` (`admin:portfolios`).

## Invariants & gotchas

- **Content groups hold product ids in JSON** — no FK/CASCADE. Missing or
  inactive products are silently dropped at read time by
  `queries/product_groups.resolve_groups` (one catalog query per request).
- Public reads are cached 60 s (`app.core.cache`: in-process dict, or Redis
  when `REDIS_URL` is set). Every Action mutation busts the matching keys
  AFTER commit — a portfolio slug edit busts the old slug (the new one was
  never cached), plus the list key.
- `app/core/content_defaults.py` **must stay in core** — Alembic migration
  `0007` imports it. Content code imports it from there (Action create,
  public landing fallback when `content` is NULL).
- Landing slug is immutable (`LandingUpdate` has no slug field — routes and
  redirects depend on it); portfolio slug IS editable but must stay unique
  (409 inside `PortfolioAction.update`).
- Inactive portfolios 404 on the public detail route, matching the public
  list (`PortfolioQuery.by_slug_public` filters `is_active`).
- The admin FAQ router keeps tags=["admin:catalog"] (it was split out of the
  old admin_catalog module) — changing it would break the OpenAPI baseline.
- Content sits ABOVE catalog in the domain DAG, so `queries/` may import
  `Product` from `app.domains.catalog` at module scope.

## Tests

`tests/test_public.py` (public landings + cache bust), `tests/test_landings.py`,
`tests/test_portfolios.py`, FAQ CRUD in `tests/test_admin_catalog.py`,
`tests/test_content_defaults.py` (core defaults unit tests).
