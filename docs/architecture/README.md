# Architecture docs — index

**The living contract is [`backend/app/domains/CLAUDE.md`](../../backend/app/domains/CLAUDE.md)**
(canonical skeleton, layer access table, naming). Files `01–06` below are the
**historical record** of the 2026-08 domain migration — accurate then, not
maintained since; `openapi-baseline.json` and this README are living.

| File | Status | What |
|---|---|---|
| `01-current-state.md` | historical | pre-migration layer-first snapshot |
| `02-domain-map.md` | historical | domain→models→routers map + DAG (predates chat) |
| `03-target-structure.md` | historical | migration target; its non-goals (repositories, CQRS) landed later — see below |
| `04-migration-plan.md` | historical | per-commit plan + the verification loop still in use |
| `05-findings.md` | historical | 9 issues found; #1 (router commits) and #8 (0019 enum) since fixed |
| `06-final-report.md` | historical | migration acceptance evidence |
| `support-chat.md` | living | WebSocket + Redis pub/sub design |
| `openapi-baseline.json` | living | frozen API contract — refactors must diff empty (`backend/scripts/dump_openapi.py`) |

## Module table (living — update when a domain changes shape)

All domains follow the canonical skeleton (`models/ schemas/ queries/ actions/
routers/ services/` — folders only where content exists). Details, invariants
and gotchas live in each domain's `README.md`.

| Domain | Purpose | Key classes | Notes |
|---|---|---|---|
| `orders` | checkout, tracking, admin orders, SMS alerts | `OrderQuery`, `CreateOrderAction`, `OrderAction` | **reference implementation**; totals in grams; public router registered before catalog |
| `catalog` | products, CSV/ZIP + MinIO imports | `ProductQuery`, `ProductAction`, `ImportJobQuery/Action` | import workers own their sessions (`services/`) |
| `customers` | OTP auth, profile, addresses, favorites | `CustomerQuery`, `RequestOtpAction`, `VerifyOtpAction`, `AddressAction`, … | `dependencies.py` at root (session deps); admin list page_size 500 > cap → own paging |
| `users` | admin auth, RBAC, audit log | `UserQuery`, `AuditLogQuery`, `UserAction` | bottom of DAG — everyone imports it; audit page_size 200 → own paging |
| `agents` | field agents: retailers, visits, gallery, agent orders | `AgentOrderQuery/Action`, `GalleryQuery/Action`, … | top of DAG; quick-sell uses `with_for_update` row lock |
| `serials` | authenticity serials, warranty, buyback | `SerialQuery/Action`, `WarrantyQuery`, `BuybackQuery`, `ActivateWarrantyAction`, `BuybackAction` | `SerialAction.generate_for_order` is idempotent and does NOT commit (caller's tx) |
| `content` | landings, FAQs, portfolios | `LandingQuery/Action`, `PortfolioQuery/Action`, `FaqQuery/Action` | cache-bust helpers in `services/cache.py`; `core/content_defaults.py` pinned by migration 0007 |
| `pricing` | gold price board (TGJU scrape) | `PriceQuery`, `PriceAction` | scraper (`services/tgju.py`) runs from lifespan loop with its own sessions |
| `chat` | live support chat (WS + Redis pub/sub) | `ConversationQuery/Action`, `MessageQuery`, `MessageAction` | design: `support-chat.md`; keyset paging limit 200 → own paging |
| `dashboard` | admin stats (read-only aggregation) | `DashboardQuery` | no actions by design — read-only domain |

## Post-Task Doc Sync (do this at the end of every task)

| When you… | Update |
|---|---|
| add/change routes, invariants, or gotchas in a domain | that domain's `README.md` |
| change the skeleton, layer rules, or naming | `backend/app/domains/CLAUDE.md` + this table |
| deliberately change the API surface | `openapi-baseline.json` (same commit, via `dump_openapi.py`) |
| add a domain or change a domain's shape | module table above + import-linter contracts in `backend/pyproject.toml` |
| add a dependency or dev command | root `CLAUDE.md` stack/commands section |
| change deploy/infra (compose, Caddy, CI) | `docs/deploy-vps.md` |
| add frontend components/composables to a domain group | `frontend/README.md` if placement rules change |
