# users

Panel users and roles (WO 7.15), admin/agent auth resolution, and the audit
log. This domain is the **bottom of the domain DAG** — nearly every admin
router imports `require_admin` from its public API, so the `__init__.py`
surface must stay a strict superset across refactors.

## Layout

| Path | What lives here |
|---|---|
| `models/user.py` | `User`, `AdminRole` (role enum), `AuditLog` |
| `schemas/auth.py` | `LoginIn`, `MeOut` |
| `schemas/user.py` | `UserCreate/Update/Out`, `AuditOut`, `AuditListOut` |
| `queries/user_query.py` | `UserQuery` — list, active-by-username, agent retailer ids |
| `queries/audit_log_query.py` | `AuditLogQuery` — filtered/paged audit listing |
| `actions/user_action.py` | `UserAction` — login (+audit row), user CRUD, retailer assignment |
| `routers/auth.py` | `/admin/login`, `/admin/logout`, `/admin/me` |
| `routers/admin_users.py` | superadmin user CRUD + agent retailer assignment |
| `routers/admin_audit.py` | superadmin audit-log listing |
| `dependencies.py` | `require_admin` / `require_agent` / `require_superadmin` / `resolve_admin` — stays at domain root; imported by nearly every admin router |

## Routes

Auth: `POST /admin/login` (rate-limited 10/min), `POST /admin/logout`,
`GET /admin/me`. Superadmin: `GET/POST /admin/users`,
`PATCH/DELETE /admin/users/{id}`, `GET/PUT /admin/users/{id}/retailers`,
`GET /admin/audit`.

## Invariants & gotchas

- The env-var admin (`settings.admin_username`) is a zero-config bootstrap
  superadmin **outside the users table** — login and `resolve_admin` both
  special-case it before touching the DB.
- Role is resolved fresh per request in `dependencies.py` so deactivation /
  role changes bite immediately; the module was moved verbatim from
  `app/api/deps.py` and is deliberately self-contained (its own select, no
  Query object) because it runs on nearly every admin request.
- Login writes its own `AuditLog` row inside `UserAction.login` — it's the one
  mutation the audit middleware (`app/main.py`) can't attribute (no cookie
  yet). All other mutating admin requests are audited by that middleware.
- Self-lockout guards live in `UserAction`: a superadmin can't deactivate,
  re-role, or delete themselves.
- `/admin/audit` allows `page_size` up to 200 — above the shared
  `MAX_PAGE_SIZE` (100) cap — so `AuditLogQuery.admin_page` keeps its own
  offset/limit instead of `BaseQuery.page()`.
- Retailer assignment reads/writes `AgentRetailer` from the **agents** domain
  (an upward DAG exception): agents' public API imports users, so agents is
  imported lazily inside `UserQuery.retailer_ids` / `UserAction.set_retailers`
  with matching `ignore_imports` entries in `pyproject.toml`.
- `AuditLog.actor` is the username string (works for the env bootstrap admin,
  survives user deletion); it is truncated to 60 chars on write.

## Tests

`tests/test_auth.py`, `tests/test_rbac.py`, `tests/test_security.py`,
`tests/test_deps.py`, plus fixture overrides of `require_admin` /
`require_superadmin` in `tests/conftest.py` used across all admin suites.
