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

## Roadmap (not done yet)

1. **userId at login** — `_paq.push(['setUserId', phone])` after OTP verify
   (and `resetUserId` on logout): joins a visitor's sessions across devices;
   enables per-customer journeys. Small frontend change.
2. **Server-side events** — chat started / OTP sent via the Tracking HTTP API
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
