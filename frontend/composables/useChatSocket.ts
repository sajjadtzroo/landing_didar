/**
 * One chat WebSocket with ticket auth, exponential-backoff reconnect and an
 * outbound queue that flushes on reopen. Shared by the customer widget and
 * the admin inbox — they differ only in the ticket endpoint and event handler.
 *
 * Server events arrive as {type: ...} (relayed fan-out) or {t: ...} (direct
 * replies like ack/pong/error); `onEvent` receives both, normalized to `.kind`.
 */
export interface ChatEvent {
  kind: string
  [k: string]: unknown
}

export function createChatSocket(opts: {
  ticketPath: string // e.g. '/account/chat/ws-ticket'
  onEvent: (e: ChatEvent) => void
  onOpen?: () => void
}) {
  const config = useRuntimeConfig()
  let ws: WebSocket | null = null
  let wantOpen = false
  let attempts = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const queue: string[] = []
  const connected = ref(false)

  function wsUrl(ticket: string): string {
    // Explicit override first; otherwise derive from the API base (dev).
    const base =
      (config.public.wsBase as string) ||
      (config.public.apiBase as string).replace(/^http/, 'ws')
    return `${base.replace(/^http/, 'ws')}/chat/ws?ticket=${encodeURIComponent(ticket)}`
  }

  async function connect() {
    wantOpen = true
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
    try {
      const { ticket } = await apiFetch<{ ticket: string }>(opts.ticketPath, {
        method: 'POST',
      })
      ws = new WebSocket(wsUrl(ticket))
    } catch {
      scheduleReconnect()
      return
    }
    ws.onopen = () => {
      connected.value = true
      attempts = 0
      while (queue.length) ws!.send(queue.shift()!)
      opts.onOpen?.()
    }
    ws.onmessage = (m) => {
      try {
        const data = JSON.parse(m.data)
        opts.onEvent({ kind: data.type || data.t, ...data })
      } catch {
        /* ignore unparseable frames */
      }
    }
    ws.onclose = () => {
      connected.value = false
      ws = null
      if (wantOpen) scheduleReconnect()
    }
    ws.onerror = () => ws?.close()
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    const delay = Math.min(1000 * 2 ** attempts++, 30_000)
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      if (wantOpen) connect()
    }, delay)
  }

  /** Send now, or queue for the next open socket. Returns false if queued. */
  function send(frame: Record<string, unknown>): boolean {
    const raw = JSON.stringify(frame)
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(raw)
      return true
    }
    queue.push(raw)
    return false
  }

  function close() {
    wantOpen = false
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
    ws?.close()
    ws = null
    connected.value = false
  }

  return { connect, send, close, connected }
}
