# agents

Field sales (WO 7.5–7.6): which retailers an agent serves, on-behalf orders
with basic delivery, visit notes, and the گالری سیار (mobile gallery) — the
bag of physical pieces an agent carries, with quick sale. This domain sits at
the **top of the domain DAG**: it may import every other domain's public API.

## Layout

| Path | What lives here |
|---|---|
| `models/agent.py` | `AgentRetailer` (assignment link), `AgentVisit`, `MobileGalleryItem` |
| `schemas/agent.py` | agent-facing DTOs — deliberately WITHOUT admin-only order fields |
| `queries/agent_retailer_query.py` | `AgentRetailerQuery` — assigned retailers + the assignment 404 guard |
| `queries/agent_order_query.py` | `AgentOrderQuery` — the agent's own orders (+ superadmin oversight) |
| `queries/agent_visit_query.py` | `AgentVisitQuery` — visit notes per agent/retailer |
| `queries/gallery_query.py` | `GalleryQuery` — bag contents, ownership guard, agent picker |
| `actions/agent_order_action.py` | `AgentOrderAction` — place on behalf of a retailer, deliver + mint serials |
| `actions/agent_visit_action.py` | `AgentVisitAction` — log a field-visit note |
| `actions/gallery_action.py` | `GalleryAction` — assign to bag, return, quick sell |
| `routers/agent.py` | everything under `/agent/*` (all `Depends(require_agent)`) |
| `routers/admin_gallery.py` | `/admin/mobile-gallery*` (hand out / take back / inspect bags) |

## Routes

Agent (`/agent`, tags=["agent"]): `GET /retailers`, `POST/GET /orders`,
`POST /orders/{id}/deliver`, `POST/GET /visits`, `GET /gallery`,
`POST /gallery/{id}/sell`. Admin (tags=["admin:gallery"]):
`GET /admin/mobile-gallery/agents`, `GET/POST /admin/mobile-gallery`,
`PATCH /admin/mobile-gallery/{id}/return`.

## Invariants & gotchas

- **Assignment is the security boundary**: every retailer-scoped endpoint goes
  through `AgentRetailerQuery.assigned_customer_or_404` first; a retailer not
  assigned to the agent is indistinguishable from a missing one (same 404).
  Same pattern for orders (`owned_or_404`, superadmin excepted) and gallery
  items — never a 403 that would confirm existence.
- On-behalf orders take identity (name/phone/store) from the retailer's
  profile server-side; the agent's form only supplies items/province/note.
  `contact_method="agent"`; `agent_id` is stamped in a second commit after
  `CreateOrderAction` has safely persisted the order.
- Agent delivery mints authenticity serials **exactly like the admin path**:
  `OrderAction.change_status` (no commit) + `serials.service.generate_for_order`,
  then one commit in `AgentOrderAction.deliver`.
- `AgentOrderOut` deliberately omits admin-only fields (`internal_note`,
  `is_read`, attribution) — don't "fix" that by reusing admin schemas.
- Gallery: a piece is in at most one bag at a time (partial unique index on
  `with_agent`); quick sale is only for `sellable` + `with_agent` items and
  row-locks the serial (`with_for_update`) so concurrent sells can't double-
  sell; the serial flips to `sold` with a passport event, no order row.
- `users` lazily imports this domain's `AgentRetailer` (see DAG
  `ignore_imports` in `pyproject.toml`) — don't turn that into a module-scope
  cycle from this side.

## Tests

`tests/test_agent.py`, `tests/test_mobile_gallery.py`.
