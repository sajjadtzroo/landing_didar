# Live support chat — design

Human-to-human support chat: customers message from a widget on the shop,
staff answer from an admin inbox. Not an LLM bot — both sides send, so the
transport is WebSocket (not SSE), fan-out is Redis Pub/Sub (not Streams),
and there is a routing/assignment layer a bot doesn't need.

## Architecture

```
Customer widget (Nuxt)          Admin inbox (Nuxt)
        │  WS                          │  WS
        └──────────► FastAPI (N processes) ◄─────┘
                         │            │
                   PostgreSQL      Redis
                   source of       pub/sub fan-out,
                   truth           presence, unread, queue
```

Each API process holds only its own local WebSocket connections. When a
message arrives, it writes to Postgres, then publishes to `chan:conv:{id}` —
every process with a subscriber on that conversation relays to its local
sockets. **This applies to us even on a single Liara replica: gunicorn runs
2 worker processes, so a customer on worker A and an agent on worker B
already need the Redis relay.**

## Fit to this codebase

- **Customer identity**: existing `customers` table + phone-OTP session
  (`didar_customer` cookie). The widget authenticates with the same cookie;
  anonymous visitors get prompted to log in (or a guest-session variant later).
- **Agent identity**: today there is exactly one admin account. Day one is
  single-agent: skip `departments`, the unassigned queue, transfer, and
  routing entirely — every conversation is implicitly assigned. The schema
  below keeps the columns (nullable) so adding a second agent later is a
  feature, not a migration.
- **Redis**: already configured (`settings.redis_url`, used by cache +
  rate limiter). Realtime keys go in the same instance until scale says
  otherwise; revisit the `noeviction` split if memory pressure ever appears.
- **Attachments**: reuse the MinIO private bucket + backend `/media` proxy,
  same as product/order uploads.
- **Observability**: structured logs already ship to Loki; include
  `conv_id`/`user_id` in chat log records from day one.

## Storage

```sql
conversations(              -- one per customer support thread
  id uuid pk, customer_id uuid, subject text,
  status text,              -- open|assigned|pending|resolved|closed
  priority smallint, channel text,   -- widget|telegram|email
  assigned_agent_id uuid null, department_id uuid null,
  first_response_at, resolved_at, closed_at,
  created_at, updated_at, last_message_at, meta jsonb)

participants(               -- who is in the room, incl. transfers
  conversation_id fk, user_id, role,   -- customer|agent|supervisor
  joined_at, left_at, last_read_message_id uuid,
  pk(conversation_id, user_id))

messages(
  id uuid pk, conversation_id fk, sender_id uuid,
  sender_role text,         -- customer|agent|system
  kind text,                -- text|file|image|system_event
  content text, client_msg_id uuid,
  status text,              -- sent|delivered|read|failed
  reply_to_id uuid, edited_at, deleted_at,
  created_at, meta jsonb)

attachments(id, message_id fk, storage_key, mime, size_bytes, scanned bool)
conversation_events(id, conversation_id fk, actor_id, type, payload jsonb)
                            -- assigned, transferred, tagged, closed, reopened
canned_responses(id, department_id null, shortcut, title, body)
agents(user_id pk, display_name, status, max_concurrent int, departments uuid[])
```

Indexes: `messages(conversation_id, created_at DESC, id)` for keyset paging,
`conversations(assigned_agent_id, status, last_message_at DESC)` for the agent
inbox, `conversations(status, priority DESC, created_at)` for the unassigned
queue, unique `(conversation_id, client_msg_id)` for retry dedupe.

`conversation_events` is worth having from day one — "who transferred this to
whom and when" is the first question every supervisor asks, and reconstructing
it later from logs is miserable.

## Redis key map

Cache-ish (safe to lose):

```
cache:conv:{id}:meta             conversation header, TTL 5m
cache:canned:{dept_id}           canned responses, TTL 1h
```

Realtime:

```
chan:conv:{conv_id}              Pub/Sub — message fan-out
chan:agent:{agent_id}            Pub/Sub — inbox updates, new assignment
chan:dept:{dept_id}              Pub/Sub — new unassigned conversation

presence:user:{user_id}          SET connection_count, TTL 60s (heartbeat)
presence:conv:{conv_id}          SET of user_ids currently viewing
typing:{conv_id}:{user_id}       SET "1" EX 5           ← auto-expiring typing
unread:{user_id}:{conv_id}       counter, INCR / DEL on read
agent:load:{agent_id}            active conversation count, for routing
queue:dept:{dept_id}             ZSET waiting convs, score = priority+time
idem:{user}:{client_msg_id}      SET NX EX 600
rl:msg:{user_id}                 rate limit
outbox:{user_id}                 LIST, TTL 24h — missed events while offline
```

Typing indicators as expiring keys instead of explicit stop events is the
small trick that saves you: if a socket dies mid-typing, the indicator clears
itself in 5s instead of hanging forever.

## WebSocket protocol

```
WS /ws?token=...                 one socket per user, multiplexed by conv_id
```

Client → server: `subscribe` / `unsubscribe {conv_id}`,
`message {conv_id, client_msg_id, content, reply_to_id?}`, `typing {conv_id}`,
`read {conv_id, up_to_message_id}`, `ping`.

Server → client: `message`, `message_ack {client_msg_id, server_id,
created_at}`, `typing {conv_id, user_id}`, `presence {user_id, online}`,
`read_receipt`, `conversation_updated` (status/assignment change),
`queue_update` (agents only), `error`, `pong`.

Authorize on every `subscribe` — check the user is an active participant or an
agent with department access. Don't trust the client's claim to a `conv_id`;
this is the most common hole in support-chat systems, where any authenticated
customer can subscribe to any conversation by guessing a UUID.

## REST endpoints

```
POST   /api/v1/conversations                  customer opens a thread
GET    /api/v1/conversations?status=&cursor=  customer: own; agent: assigned
GET    /api/v1/conversations/{id}
GET    /api/v1/conversations/{id}/messages?before=&limit=
POST   /api/v1/conversations/{id}/messages    HTTP fallback when WS is down
POST   /api/v1/conversations/{id}/read
POST   /api/v1/conversations/{id}/attachments presigned upload

# agent / admin
GET    /api/v1/admin/queue?department=        unassigned, sorted
POST   /api/v1/admin/conversations/{id}/assign      {agent_id} or self-claim
POST   /api/v1/admin/conversations/{id}/transfer    {to_agent_id|to_department}
POST   /api/v1/admin/conversations/{id}/status      resolve / close / reopen
POST   /api/v1/admin/conversations/{id}/notes       internal, invisible to customer
GET    /api/v1/admin/agents/me/stats
PATCH  /api/v1/admin/agents/me/status               online|away|offline
GET    /api/v1/admin/search?q=&from=&to=
```

Claiming from the queue must be atomic — `ZPOPMIN` on `queue:dept:{id}` plus a
conditional `UPDATE conversations SET assigned_agent_id=$1 WHERE id=$2 AND
assigned_agent_id IS NULL`. Two agents clicking the same waiting customer at
the same moment is not a rare edge case on a busy shift.

## Nuxt side

Two surfaces, one API. The **customer widget** is a small embeddable
component: floating launcher, unread badge, message list, file input. The
**admin inbox** is three panes — queue/assigned list left, thread center,
customer context right (past conversations, order history, internal notes).

One `useRealtime()` composable owns the single WebSocket with
exponential-backoff reconnect and an outbound queue that flushes on reopen.
Pinia stores split by concern: `conversations`, `messagesByConv`, `presence`,
`typing`, `unread`. Optimistic send with `client_msg_id`, reconciled on
`message_ack`.

On reconnect, don't replay from the socket — call
`GET /messages?after={last_seen_id}` per open conversation. Pub/Sub is
fire-and-forget by design, so Postgres is the only honest way to close a gap.

## Phasing

1. **Core** — schema, auth, conversation/message REST, customer widget with
   polling. Ugly but correct.
2. **Realtime** — WebSocket, Redis Pub/Sub relay, presence, typing, read
   receipts, reconnect gap-fill.
3. **Agent workflow** — *only when a second agent exists*: queue, assignment,
   transfer, status lifecycle, internal notes, canned responses.
4. **Hardening** — rate limits, attachment scanning, per-conversation
   authorization tests, `conv_id`/`user_id` in Loki logs.
5. **Ops** — SLA timers (first response, resolution), agent dashboards,
   transcript export, business-hours auto-replies.

For this shop, phases 1–2 are the product; 3+ activate as the team grows.

## Failure modes designed against explicitly

- **Pub/Sub loss on reconnect** → `after=` gap-fill from Postgres.
- **Double assignment from the queue** → conditional UPDATE above.
- **Unbounded sockets per user** → cap connections per user_id, or one
  customer with ten tabs eats a process's file descriptors.
