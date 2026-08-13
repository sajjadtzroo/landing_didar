<script setup lang="ts">
// Admin support inbox: conversation list + thread pane, live over the same
// WS protocol as the widget (admin sockets also receive the chat:admin feed).
import { CheckCheck, MessageCircle, RotateCcw, Send } from 'lucide-vue-next'
import type { ChatAdminConversation, ChatMessage } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const convs = ref<ChatAdminConversation[]>([])
const current = ref<ChatAdminConversation | null>(null)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const customerTyping = ref(false)
const listEl = ref<HTMLElement | null>(null)
let typingTimer: ReturnType<typeof setTimeout> | null = null

const STATUS_LABEL: Record<string, string> = {
  open: 'باز',
  resolved: 'حل‌شده',
  closed: 'بسته',
}

async function loadConvs() {
  convs.value = await apiFetch<ChatAdminConversation[]>('/admin/chat/conversations')
}

function upsertMessage(msg: ChatMessage) {
  const i = messages.value.findIndex(
    (m) =>
      m.id === msg.id ||
      (msg.client_msg_id && m.client_msg_id === msg.client_msg_id),
  )
  if (i >= 0) messages.value[i] = msg
  else messages.value.push(msg)
}

async function scrollDown() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight })
}

const socket = createChatSocket({
  ticketPath: '/admin/chat/ws-ticket',
  onEvent: (e) => {
    if (e.kind === 'message') {
      const msg = e.message as ChatMessage
      if (current.value && msg.conversation_id === current.value.id) {
        upsertMessage(msg)
        void scrollDown()
        if (msg.sender_role === 'customer') {
          socket.send({ t: 'read', conv_id: current.value.id })
        }
      }
      // Inbox feed: bump preview + unread on the list row.
      const row = convs.value.find((c) => c.id === msg.conversation_id)
      if (row) {
        row.last_message = msg.content
        row.last_message_at = msg.created_at
        if (
          msg.sender_role === 'customer' &&
          (!current.value || current.value.id !== msg.conversation_id)
        ) {
          row.unread++
        }
      } else {
        void loadConvs() // unknown thread — refetch the list
      }
    } else if (e.kind === 'ack') {
      upsertMessage(e.message as ChatMessage)
    } else if (e.kind === 'typing' && e.role === 'customer') {
      if (current.value && e.conv_id === current.value.id) {
        customerTyping.value = true
        if (typingTimer) clearTimeout(typingTimer)
        typingTimer = setTimeout(() => (customerTyping.value = false), 5000)
      }
    } else if (e.kind === 'conversation') {
      void loadConvs()
    }
  },
  onOpen: () => {
    if (current.value) socket.send({ t: 'sub', conv_id: current.value.id })
  },
})

async function openConv(c: ChatAdminConversation) {
  current.value = c
  customerTyping.value = false
  messages.value = await apiFetch<ChatMessage[]>(
    `/admin/chat/conversations/${c.id}/messages`,
    { params: { limit: 100 } },
  )
  socket.send({ t: 'sub', conv_id: c.id })
  socket.send({ t: 'read', conv_id: c.id })
  c.unread = 0
  void scrollDown()
}

async function send() {
  const text = draft.value.trim()
  if (!text || !current.value) return
  draft.value = ''
  const client_msg_id = crypto.randomUUID()
  upsertMessage({
    id: client_msg_id,
    conversation_id: current.value.id,
    sender_role: 'admin',
    content: text,
    client_msg_id,
    created_at: new Date().toISOString(),
    pending: true,
  })
  void scrollDown()
  const ok = socket.send({
    t: 'msg',
    conv_id: current.value.id,
    client_msg_id,
    content: text,
  })
  if (!ok) {
    const msg = await apiFetch<ChatMessage>(
      `/admin/chat/conversations/${current.value.id}/messages`,
      { method: 'POST', body: { content: text, client_msg_id } },
    )
    upsertMessage(msg)
  }
}

async function setStatus(status: 'open' | 'resolved' | 'closed') {
  if (!current.value) return
  await apiFetch(`/admin/chat/conversations/${current.value.id}/status`, {
    method: 'POST',
    body: { status },
  })
  current.value.status = status
  void loadConvs()
}

function timeOf(iso: string): string {
  return new Date(iso).toLocaleTimeString('fa-IR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
function dayOf(iso: string): string {
  return new Date(iso).toLocaleDateString('fa-IR', {
    month: 'short',
    day: 'numeric',
  })
}

onMounted(() => {
  void loadConvs()
  void socket.connect()
})
onBeforeUnmount(() => socket.close())
</script>

<template>
  <div class="flex h-[calc(100dvh-7rem)] gap-4">
    <!-- Conversation list -->
    <aside class="flex w-80 shrink-0 flex-col overflow-hidden rounded-2xl border border-line bg-surface">
      <header class="border-b border-line px-4 py-3">
        <h1 class="text-sm font-bold text-ink">گفتگوهای پشتیبانی</h1>
      </header>
      <div class="flex-1 overflow-y-auto">
        <p v-if="!convs.length" class="p-6 text-center text-sm text-ink/50">
          هنوز گفتگویی شروع نشده است.
        </p>
        <button
          v-for="c in convs"
          :key="c.id"
          class="block w-full border-b border-line px-4 py-3 text-start hover:bg-surface-2"
          :class="current?.id === c.id ? 'bg-surface-2' : ''"
          @click="openConv(c)"
        >
          <div class="flex items-center gap-2">
            <p class="min-w-0 flex-1 truncate text-sm font-bold text-ink">
              {{ c.customer_name || toFa(c.customer_phone) }}
            </p>
            <span
              v-if="c.unread"
              class="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-bold text-white"
            >
              {{ toFa(String(c.unread)) }}
            </span>
            <span class="text-[11px] text-ink/40">{{ dayOf(c.last_message_at) }}</span>
          </div>
          <div class="mt-1 flex items-center gap-2">
            <p class="min-w-0 flex-1 truncate text-xs text-ink/60">
              {{ c.last_message || '—' }}
            </p>
            <span
              class="rounded-full px-2 py-0.5 text-[10px]"
              :class="
                c.status === 'open'
                  ? 'bg-success-soft text-success'
                  : 'bg-surface-2 text-ink/50'
              "
            >
              {{ STATUS_LABEL[c.status] }}
            </span>
          </div>
        </button>
      </div>
    </aside>

    <!-- Thread -->
    <section class="flex min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-line bg-surface">
      <div
        v-if="!current"
        class="flex flex-1 flex-col items-center justify-center gap-3 text-ink/40"
      >
        <MessageCircle class="h-10 w-10" />
        <p class="text-sm">یک گفتگو را انتخاب کنید.</p>
      </div>

      <template v-else>
        <header class="flex items-center gap-3 border-b border-line px-4 py-3">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-bold text-ink">
              {{ current.customer_name || toFa(current.customer_phone) }}
            </p>
            <p class="text-xs text-ink/50">
              {{ toFa(current.customer_phone) }} ·
              {{ STATUS_LABEL[current.status] }}
              <span v-if="!socket.connected.value" class="text-warning"> · در حال اتصال…</span>
            </p>
          </div>
          <button
            v-if="current.status === 'open'"
            class="flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs text-ink hover:bg-surface-2"
            @click="setStatus('resolved')"
          >
            <CheckCheck class="h-4 w-4" /> حل شد
          </button>
          <button
            v-else
            class="flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs text-ink hover:bg-surface-2"
            @click="setStatus('open')"
          >
            <RotateCcw class="h-4 w-4" /> بازکردن
          </button>
        </header>

        <div ref="listEl" class="flex-1 space-y-2 overflow-y-auto p-4">
          <div
            v-for="m in messages"
            :key="m.id"
            class="flex"
            :class="m.sender_role === 'admin' ? 'justify-start' : 'justify-end'"
          >
            <div
              class="max-w-[70%] rounded-2xl px-3 py-2 text-sm leading-6"
              :class="[
                m.sender_role === 'admin'
                  ? 'rounded-br-sm bg-navy text-white'
                  : 'rounded-bl-sm border border-line bg-surface-2 text-ink',
                m.pending ? 'opacity-60' : '',
              ]"
            >
              <p class="whitespace-pre-wrap break-words">{{ m.content }}</p>
              <p class="mt-1 text-[10px] opacity-60">{{ timeOf(m.created_at) }}</p>
            </div>
          </div>
          <p v-if="customerTyping" class="px-2 text-xs text-ink/50">
            مشتری در حال نوشتن است…
          </p>
        </div>

        <form
          class="flex items-center gap-2 border-t border-line p-3"
          @submit.prevent="send"
        >
          <input
            v-model="draft"
            type="text"
            placeholder="پاسخ خود را بنویسید…"
            maxlength="4000"
            class="min-w-0 flex-1 rounded-full border border-line bg-surface-2 px-4 py-2 text-sm text-ink outline-none focus:border-navy"
          />
          <button
            type="submit"
            :disabled="!draft.trim()"
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-navy text-white disabled:opacity-40"
            aria-label="ارسال"
          >
            <Send class="h-4 w-4 -scale-x-100" />
          </button>
        </form>
      </template>
    </section>
  </div>
</template>
