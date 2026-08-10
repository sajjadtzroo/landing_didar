/**
 * Client-side error reporting: queue + batched flush to the backend's
 * /api/v1/logs ingest (rate-limited server-side). Fire-and-forget — logging
 * must never break the app or spam the network (max 20/batch, flush on a
 * 5s timer and on pagehide via sendBeacon).
 */

interface ClientLogEntry {
  level?: 'info' | 'warn' | 'error'
  module?: string
  event: string
  message: string
  url?: string
  stack?: string
}

const queue: ClientLogEntry[] = []
let timer: ReturnType<typeof setTimeout> | null = null

function endpoint(): string {
  const config = useRuntimeConfig()
  return `${config.public.apiBase}/logs`
}

function flush() {
  timer = null
  if (!queue.length) return
  const logs = queue.splice(0, 20)
  // keepalive lets the request survive navigation; errors are swallowed.
  fetch(endpoint(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ logs }),
    keepalive: true,
  }).catch(() => {})
}

export function reportClientError(entry: ClientLogEntry) {
  if (queue.length >= 50) return // hard cap: never grow unbounded
  queue.push({
    level: 'error',
    module: 'nuxt.client',
    ...entry,
    message: String(entry.message).slice(0, 2000),
    stack: entry.stack?.slice(0, 4000),
  })
  if (!timer) timer = setTimeout(flush, 5000)
}

export function flushClientLogs() {
  if (!queue.length) return
  const logs = queue.splice(0, 20)
  navigator.sendBeacon?.(
    endpoint(),
    new Blob([JSON.stringify({ logs })], { type: 'application/json' })
  )
}
