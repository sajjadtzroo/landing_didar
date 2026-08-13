/**
 * Customer support chat state: one conversation, its messages, unread count.
 * Optimistic send with client_msg_id (reconciled on ack), REST gap-fill on
 * every (re)connect — Pub/Sub drops are recovered from Postgres, never the
 * socket. WS falls back to plain REST send when the socket is down.
 */
import type { ChatConversation, ChatMessage } from '~/types'

export function useSupportChat() {
  const conv = useState<ChatConversation | null>('chat-conv', () => null)
  const messages = useState<ChatMessage[]>('chat-messages', () => [])
  const unread = useState<number>('chat-unread', () => 0)
  const panelOpen = useState<boolean>('chat-open', () => false)
  const agentTyping = useState<boolean>('chat-typing', () => false)

  let socket: ReturnType<typeof createChatSocket> | null = null
  let typingTimer: ReturnType<typeof setTimeout> | null = null
  let lastTypingSent = 0

  const CHAT = '/account/chat'

  function lastId(): string | null {
    const real = messages.value.filter((m) => !m.pending)
    return real.length ? real[real.length - 1].id : null
  }

  function upsert(msg: ChatMessage) {
    // Reconcile the optimistic copy (same client_msg_id) or dedupe redelivery.
    const i = messages.value.findIndex(
      (m) =>
        m.id === msg.id ||
        (msg.client_msg_id && m.client_msg_id === msg.client_msg_id),
    )
    if (i >= 0) messages.value[i] = msg
    else messages.value.push(msg)
  }

  async function gapFill() {
    if (!conv.value) return
    const after = lastId()
    const rows = await apiFetch<ChatMessage[]>(
      `${CHAT}/conversations/${conv.value.id}/messages`,
      { params: after ? { after } : { limit: 50 } },
    )
    rows.forEach(upsert)
  }

  function handleEvent(e: { kind: string; [k: string]: unknown }) {
    if (e.kind === 'message') {
      const msg = e.message as ChatMessage
      upsert(msg)
      if (msg.sender_role === 'admin') {
        if (panelOpen.value) void markRead()
        else unread.value++
      }
    } else if (e.kind === 'ack') {
      upsert(e.message as ChatMessage)
    } else if (e.kind === 'typing' && e.role === 'admin') {
      agentTyping.value = true
      if (typingTimer) clearTimeout(typingTimer)
      typingTimer = setTimeout(() => (agentTyping.value = false), 5000)
    } else if (e.kind === 'conversation') {
      const c = e.conv as ChatConversation
      if (conv.value && c.id === conv.value.id) conv.value = c
    }
  }

  async function open() {
    panelOpen.value = true
    unread.value = 0
    useAnalytics().trackEvent('chat', 'open')
    if (!conv.value) {
      conv.value = await apiFetch<ChatConversation>(`${CHAT}/conversations`, {
        method: 'POST',
        body: {},
      })
    }
    await gapFill()
    void markRead()
    if (!socket) {
      socket = createChatSocket({
        ticketPath: `${CHAT}/ws-ticket`,
        onEvent: handleEvent,
        onOpen: () => {
          socket!.send({ t: 'sub', conv_id: conv.value!.id })
          void gapFill() // close any gap from the offline window
        },
      })
    }
    void socket.connect()
  }

  function closePanel() {
    panelOpen.value = false
    // Keep the socket: new replies bump the launcher badge in realtime.
  }

  async function send(content: string) {
    if (!conv.value || !content.trim()) return
    // First message of the session = a support conversation actually started.
    if (!messages.value.some((m) => m.sender_role === 'customer')) {
      const { trackEvent, trackGoal } = useAnalytics()
      trackEvent('chat', 'first-message')
      trackGoal(Number(useRuntimeConfig().public.matomoGoalChat))
    }
    const client_msg_id = crypto.randomUUID()
    upsert({
      id: client_msg_id, // placeholder until ack
      conversation_id: conv.value.id,
      sender_role: 'customer',
      content: content.trim(),
      client_msg_id,
      created_at: new Date().toISOString(),
      pending: true,
    })
    const sent = socket?.send({
      t: 'msg',
      conv_id: conv.value.id,
      client_msg_id,
      content: content.trim(),
    })
    if (!sent) {
      // Socket down/queued — REST is the source of truth anyway.
      const msg = await apiFetch<ChatMessage>(
        `${CHAT}/conversations/${conv.value.id}/messages`,
        { method: 'POST', body: { content: content.trim(), client_msg_id } },
      )
      upsert(msg)
    }
  }

  function sendTyping() {
    if (!conv.value || !socket) return
    const now = Date.now()
    if (now - lastTypingSent > 3000) {
      lastTypingSent = now
      socket.send({ t: 'typing', conv_id: conv.value.id })
    }
  }

  async function markRead() {
    if (!conv.value) return
    unread.value = 0
    socket?.send({ t: 'read', conv_id: conv.value.id })
  }

  return {
    conv,
    messages,
    unread,
    panelOpen,
    agentTyping,
    connected: computed(() => socket?.connected.value ?? false),
    open,
    closePanel,
    send,
    sendTyping,
  }
}
