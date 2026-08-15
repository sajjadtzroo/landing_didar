# chat

Live support chat between customers and shop staff: one conversation thread
per customer episode, REST + WebSocket delivery, Redis pub/sub fan-out across
gunicorn workers. Single-agent today — no assignment, departments or routing
(design + growth path: `docs/architecture/support-chat.md`).

## Layout

| Path | What lives here |
|---|---|
| `models/conversation.py` | `Conversation`, `ChatMessage`, `ConversationStatus`, `SenderRole` |
| `schemas/chat.py` | DTOs: `MessageIn/Out`, `ConversationOut`, `ConversationAdminItem`, … |
| `queries/conversation_query.py` | `ConversationQuery` — ownership checks, customer list, admin inbox (unread-first) |
| `queries/message_query.py` | `MessageQuery` — keyset thread paging, retry lookup by `client_msg_id` |
| `actions/conversation_action.py` | `ConversationAction` — get-or-create open thread, read marks, status; `publish_conversation` fan-out helper |
| `actions/message_action.py` | `MessageAction.send` — idempotent insert, thread bump, reopen, fan-out |
| `routers/account.py` | customer endpoints under `/account/chat` (cookie auth) |
| `routers/admin.py` | staff inbox under `/admin/chat` |
| `routers/ws.py` | `/chat/ws` WebSocket loop + per-event authorization |
| `services/realtime.py` | socket registry + Redis pub/sub relay, WS tickets, `conv_channel` |
| `services/notifications.py` | best-effort admin SMS alert (fire-and-forget) |

## Routes

Customer (`/api/v1/account/chat`): `POST/GET /conversations`,
`GET/POST /conversations/{id}/messages` (send rate-limited 30/min),
`POST /conversations/{id}/read`, `POST /ws-ticket`.
Admin (`/api/v1/admin/chat`): same shapes plus `POST …/status` and the inbox
`GET /conversations` (unread counts + last-message preview).
WS: `/api/v1/chat/ws?ticket=…` (not in OpenAPI).

## Invariants & gotchas

- **One live thread per customer** — get-or-create returns the newest open
  conversation; resolved/closed ones are history. A customer writing into a
  settled thread reopens it (never forks a parallel one) and re-alerts staff.
- **Idempotent sends**: the DB unique `(conversation_id, client_msg_id)`
  guarantees retried messages land once; the handler returns the earlier row.
- Read state is two timestamps on the conversation (per side), not
  per-message status rows: unread = other side's messages newer than my mark.
- **Every write publishes its own fan-out event** (thread channel +
  `chat:admin`) so REST and WS delivery behave identically — keep publishes
  inside the Actions, next to the commit.
- WS auth is a signed 60-second ticket minted over REST (cookies don't ride
  the cross-origin upgrade). Every sub/write re-checks ownership per event;
  one DB session per event, never held across socket awaits.
- `services/realtime.py`: without `REDIS_URL` (dev, tests) `publish()`
  dispatches locally — same behavior, single process only. `stop_reader()` is
  called from `app/main.py` shutdown before the pool closes.
- Admin SMS alert is fire-and-forget and best-effort; failure must never
  break chat. Tests monkeypatch `services/notifications.py::send_sms`.
- Thread paging is keyset with a documented `limit ≤ 200` — above
  `MAX_PAGE_SIZE`, so `MessageQuery.page_messages` keeps its own limit logic
  instead of `BaseQuery.page()`.
- 404 for both missing and foreign threads (`owned_or_404`) — don't confirm
  existence to the wrong customer.

## Tests

`tests/test_chat.py` (REST flows, authorization, idempotency, WS units),
`tests/test_chat_sms.py` (admin alert on new/reopened threads). The full
socket loop is exercised against the running stack, not in unit tests.
