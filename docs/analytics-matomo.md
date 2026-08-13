# Matomo analytics — setup & plan

Instance: `https://didargold-fnebllvlkk.liara.run/` (Matomo 5.9.0, self-hosted,
site id 1, timezone Asia/Tehran, currency IRR). Admin token lives in the
gitignored root `.env` (`MATOMO_TOKEN`) — never in the repo.

## How tracking flows (already wired in the frontend)

- `useAnalytics()` is the only `_paq` surface. Order success fires
  `trackGoal(1, total)` + `trackEcommerceOrder(reference, total)` +
  custom dimensions (province → dim 1, utm source → dim 2); phone-call CTA
  fires `trackGoal(2)`. Goal/dimension ids come from `NUXT_PUBLIC_MATOMO_*`.

## Server-side state (configured 2026-08-13, via API from Claude Code)

| Thing | State |
|---|---|
| Goal 1 «ثبت سفارش» (manual, revenue) | created — was missing; conversions were silently dropped before |
| Goal 2 «تماس تلفنی» (manual) | created |
| Goal 3 «شروع گفتگوی پشتیبانی» (manual) | created; widget fires it on first customer message |
| Custom dimension 1 «استان» (visit) | created — was missing |
| Custom dimension 2 «منبع ورود» (visit) | created |
| Site main URL / aliases | didargold.ir main; www + didar-gold.liara.run aliases |
| Currency | IRR (was USD) |
| Segments | «خریداران», «بازدید موبایل», «ورود از اینستاگرام» (real-time, shared) |
| Launch annotation 2026-08-13 | didargold.ir + SSL, support chat, PayamSMS |

Conversion pipeline verified end-to-end with a Tracking-API test hit:
goal 1 and an ecommerce order both recorded with revenue 19,205,600.

## Funnels

The Funnels plugin is **premium ($229/yr for on-premise)** and is NOT
installed. Free built-ins cover most of the need at this traffic level:

- **Users Flow** (Behaviour → Users Flow): page-to-page drop-off paths.
- **Transitions** (per-page): where visitors came from / went next.
- **Goal reports + segments**: compare «خریداران» vs «بازدید موبایل» etc.
  to see which audiences convert.

Buy Funnels only when a strict step-defined funnel (shop → product → cart →
order form → success, with per-step drop-off) becomes a real weekly question.

## Section audit (2026-08-13, month-to-date)

Visitors/devices/geo, Behaviour→Pages (with page-performance timings),
events (products/order categories), ecommerce orders + abandoned carts, and
referrer types all have live data. `nb_users` was 0 → fixed by userId
tracking (below). Site Search is correctly configured (`?q=` is a default
keyword param, SPA tracks full path) — just no searches yet. Content
tracking is unused: needs `data-track-content` markup + a tracker line; add
when banner CTR becomes a question.

## Done in the same pass (frontend, e82f7c6)

- `setUserId(phone)` after OTP verify and on `/me` restore; `resetUserId`
  on logout → visitor profiles / cross-device journeys.
- Chat behavior: `chat/open` event on widget open, `chat/first-message`
  event + goal 3 on the first customer message of a session.

## Roadmap (not done yet)

1. **Server-side events** — chat started / OTP sent via the Tracking HTTP API
   from the backend, for events the browser can't see reliably.
3. **Official McpServer plugin** (free, Matomo ≥5) — install from the
   marketplace, then `claude mcp add --transport http analytics <mcp-url>
   --header 'Authorization: Bearer <token>'` for natural-language analytics
   in Claude Code sessions.
4. **View-only token** — mint a read-only user + token for day-to-day
   queries; keep the admin token out of `.env` once config work settles.
5. **Cron archiving** on the Matomo host — required if segments should be
   pre-processed (`autoArchive=1`); real-time segments are fine at current
   traffic.
