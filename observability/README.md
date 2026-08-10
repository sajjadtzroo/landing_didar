# Didar Observability Stack

Self-hosted logs + metrics + dashboards + alerting: **Loki** (log store),
**Alloy** (collector — Promtail's successor), **Grafana** (UI + alerting),
**Prometheus** (metrics), **cAdvisor/node-exporter** (infra). Total footprint
~1.2 GB RAM, fits the 4 vCPU / 8 GB VPS alongside the app stack.

## Architecture

```
browser ──errors──▶ POST /api/v1/logs ─┐
Nuxt SSR ──JSON errors──▶ stdout ──────┤
FastAPI ──JSON logs (loguru)──▶ stderr ├──▶ Docker json-file ──▶ Alloy ──▶ Loki ──▶ Grafana
Postgres ──slow queries/locks──▶ stdout┘                                      ▲
FastAPI /metrics ◀──scrape── Prometheus ──────────────────────────────────────┘
cAdvisor + node-exporter ◀──scrape── Prometheus            Grafana Alerting ──▶ Telegram
```

One shared identifier ties it together: the frontend sends `X-Request-ID` on
every API call; the backend binds it to every log line for that request
(`logger.contextualize`) and echoes it in the response. A browser error report
carries the same id → grep one id across browser, SSR, API, and DB layers.

## Run

```sh
# app stack first (it defines the network Prometheus joins)
docker compose up -d --build
# observability stack
GRAFANA_ADMIN_PASSWORD=... docker compose -f observability/docker-compose.observability.yml up -d
# one-time: enable query stats in postgres
docker exec landing_didar-db-1 psql -U didar -d didar -c 'CREATE EXTENSION IF NOT EXISTS pg_stat_statements'
```

Grafana: http://localhost:3002 (admin / $GRAFANA_ADMIN_PASSWORD). Loki,
Prometheus, Alloy, cAdvisor are internal-network only — never expose them.
For Telegram alerts set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` and restart
Grafana.

## Logging contract (backend `LOG_JSON=true`)

One flat JSON object per line on stderr:

```json
{"timestamp": "2026-08-10T11:30:00.123+03:30", "level": "INFO", "service": "didar-api",
 "env": "production", "module": "api.access", "event": "http.request",
 "request_id": "a3f9…", "status_code": 200, "duration_ms": 12.4, "pid": 7,
 "message": "GET /api/v1/products -> 200"}
```

Errors add `error: {type, message, stack}`. The Nuxt/Nitro side emits the same
shape with `service: didar-web`. Namespaces (`module`) in use:
`api.access`, `api.error`, `security`, `db.query`, `nuxt.client`, `nuxt.api`,
`nuxt.router`, `nuxt.ssr`, `stdlib.uvicorn`, plus `app` for legacy call sites.

Per-namespace levels: `LOG_LEVELS="db.query=DEBUG,api.auth=DEBUG"` (everything
else stays at `LOG_LEVEL`). New code gets a namespaced logger via
`get_logger("services.gold_prices")` from `app.core.logging`.

Redaction runs before any sink: Iranian mobile numbers are masked
(`0912****567`), OTP codes after کد/code are starred, and extra-field keys like
`password`/`token`/`authorization` are replaced with `[redacted]`.

## Useful LogQL

```logql
# everything for one request, across services
{project="landing_didar"} |= "a3f9b2c4"

# all 5xx in the last hour
{service="backend"} | json | status_code >= 500

# slow queries with duration
{service="backend"} | json | module="db.query"

# security events (rate-limit trips, auth)
{service="backend"} | json | module="security"

# browser-side errors
{service="backend"} | json | module=~"nuxt.*"

# postgres slow queries / lock waits (plain text lines)
{service="db"} |~ "duration: [0-9]{3,}"

# error rate per service, 5m buckets
sum by (service) (count_over_time({project="landing_didar", level=~"ERROR|CRITICAL"}[5m]))
```

## Dashboards

`service-overview.json` ships provisioned. Build these next in the UI (they
save to the provisioned folder):

1. **Service Overview** (shipped) — request rate by status, latency percentiles, log/error volume, live error tail, rate-limit + slow-query counters, container memory.
2. **API Deep-Dive** — per-route rate/latency/error tables from `http_requests_total{route=…}`, top slowest routes, 429s by route.
3. **Database** — slow-query log stream, `db_slow_queries_total` rate, pg connection counts (from postgres logs), pool saturation once exposed.
4. **Infra** — node CPU/mem/disk/net, per-container CPU/mem from cAdvisor, disk-growth trend on the Loki + pgdata volumes.
5. **Business pulse** — LogQL over `event="http.request"` on order/verify routes: orders/hour, serial verifications/hour, OTP requests (spike = abuse).

## Alert rules (provisioned, → Telegram)

| # | Alert | Threshold | Why this number |
|---|---|---|---|
| 1 | High 5xx rate | >5% of requests, 5m | At low traffic a tighter bar false-alarms on one retry burst; 5% sustained = real user impact |
| 2 | p95 latency | >1s, 10m | Baseline p95 <200ms; 5× degradation sustained = structural problem |
| 3 | Backend down | scrape fails 2m | Tolerates a deploy restart, catches a crash |
| 4 | Rate-limit surge | >0.5 trips/s, 15m | Limits are 5–60/min/IP; sustained trips = brute force or scraping |
| 5 | Slow queries | >0.2/s, 10m | Baseline ~0 after index review; any sustained rate is a regression |
| 6 | Disk | <15% free, 15m | 15GB runway on 100GB disk before writes fail |
| 7 | Memory | <10% available, 15m | Below that the OOM killer picks a victim (usually Postgres) |
| 8 | Log silence | 0 backend lines in 10m | Gold-price loop logs every 2m; silence = hung process or dead pipeline |

## Operational checklist

- [ ] `GRAFANA_ADMIN_PASSWORD` set (never default), Grafana behind the same reverse proxy/firewall as other internal tools
- [ ] Telegram contact point tested (Alerting → Contact points → Test)
- [ ] `CREATE EXTENSION pg_stat_statements` run once after first boot
- [ ] Loki volume on the SSD, retention 14d — revisit if `docker system df` shows growth
- [ ] App containers keep the `max-size: 20m / max-file: 5` json-file options (Alloy tails these files; rotation is handled there, not in the app)
- [ ] Grafana dashboards folder is provisioned from git — export UI changes back into `observability/grafana/dashboards/`
- [ ] Backup: `grafana-data` volume (or rely on provisioning-from-git, which this setup already gives you) and nothing else — logs/metrics are rebuildable telemetry, not source of truth
- [ ] On Liara (until the VPS move): this stack can't run there; `LOG_JSON=true` still pays off — Liara's log viewer shows the structured lines, and the contract is ready for the VPS

## Cardinality rules (what keeps Loki small)

Indexed labels are only `service`, `container`, `project`, `level` — all
bounded. `request_id`, `user_id`, `module`, routes, and messages live in the
log line and are filtered at query time (`| json | module="db.query"`). Never
promote a per-request value to a label.
