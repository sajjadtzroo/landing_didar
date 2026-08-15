<script setup lang="ts">
// Floating support-chat launcher + panel (customer side). Auth-aware: guests
// get a login CTA; the thread only loads after OTP login.
import { MessageCircle, Send, X } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'

const C = CONTENT.chat
const chat = useSupportChat()
const auth = useCustomerAuth()
const draft = ref('')
const listEl = ref<HTMLElement | null>(null)
const opening = ref(false)

const loggedIn = computed(() => !!auth.customer.value)

async function toggle() {
  if (chat.panelOpen.value) {
    chat.closePanel()
    return
  }
  opening.value = true
  try {
    await auth.ensure()
    if (auth.customer.value) await chat.open()
    else chat.panelOpen.value = true // show the login prompt panel
  } finally {
    opening.value = false
  }
}

async function submit() {
  const text = draft.value.trim()
  if (!text) return
  draft.value = ''
  await chat.send(text)
}

// Stick to the bottom whenever messages change while the panel is open.
watch(
  () => chat.messages.value.length,
  async () => {
    await nextTick()
    listEl.value?.scrollTo({ top: listEl.value.scrollHeight })
  },
)
watch(chat.panelOpen, async (open) => {
  if (open) {
    await nextTick()
    listEl.value?.scrollTo({ top: listEl.value.scrollHeight })
  }
})

function timeOf(iso: string): string {
  return new Date(iso).toLocaleTimeString('fa-IR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <!-- RTL site: cart FAB owns the end corner, chat takes the start corner.
       Raised above the mobile BottomNav (sm:hidden) + iOS safe area. -->
  <div
    class="fixed bottom-[calc(4.5rem+env(safe-area-inset-bottom))] start-4 z-40 flex flex-col items-start gap-3 sm:bottom-5"
  >
    <Transition name="chat-pop">
      <section
        v-if="chat.panelOpen.value"
        class="flex h-[28rem] max-h-[70dvh] w-[min(22rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-luxury"
        :aria-label="C.title"
      >
        <!-- Header -->
        <header class="flex items-center gap-3 bg-navy px-4 py-3 text-white">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-bold">{{ C.title }}</p>
            <p class="truncate text-xs text-white/70">
              {{ chat.connected.value || !loggedIn ? C.subtitle : C.reconnecting }}
            </p>
          </div>
          <button
            class="flex h-8 w-8 items-center justify-center rounded-full hover:bg-white/10"
            :aria-label="'بستن'"
            @click="chat.closePanel()"
          >
            <X class="h-4 w-4" />
          </button>
        </header>

        <!-- Guest: login prompt -->
        <div
          v-if="!loggedIn"
          class="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center"
        >
          <p class="text-sm leading-6 text-ink">{{ C.loginPrompt }}</p>
          <NuxtLink
            to="/account/login"
            class="rounded-full bg-navy px-5 py-2 text-sm font-bold text-white hover:opacity-90"
          >
            {{ C.loginCta }}
          </NuxtLink>
        </div>

        <!-- Thread -->
        <template v-else>
          <div ref="listEl" class="flex-1 space-y-2 overflow-y-auto p-3">
            <p
              v-if="!chat.messages.value.length"
              class="py-8 text-center text-sm text-ink/60"
            >
              {{ C.empty }}
            </p>
            <div
              v-for="m in chat.messages.value"
              :key="m.id"
              class="flex"
              :class="m.sender_role === 'customer' ? 'justify-start' : 'justify-end'"
            >
              <div
                class="max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-6"
                :class="[
                  m.sender_role === 'customer'
                    ? 'rounded-br-sm bg-navy text-white'
                    : 'rounded-bl-sm border border-line bg-surface-2 text-ink',
                  m.pending ? 'opacity-60' : '',
                ]"
              >
                <p class="whitespace-pre-wrap break-words">{{ m.content }}</p>
                <p class="mt-1 text-[10px] opacity-60">{{ timeOf(m.created_at) }}</p>
              </div>
            </div>
            <p v-if="chat.agentTyping.value" class="px-2 text-xs text-ink/50">
              {{ C.typing }}
            </p>
          </div>

          <p
            v-if="chat.conv.value && chat.conv.value.status !== 'open'"
            class="border-t border-line bg-surface-2 px-3 py-2 text-center text-xs text-ink/60"
          >
            {{ C.resolved }}
          </p>

          <!-- Composer -->
          <form
            class="flex items-center gap-2 border-t border-line p-2"
            @submit.prevent="submit"
          >
            <input
              v-model="draft"
              type="text"
              :placeholder="C.placeholder"
              maxlength="4000"
              class="min-w-0 flex-1 rounded-full border border-line bg-surface-2 px-4 py-2 text-sm text-ink outline-none focus:border-navy"
              @input="chat.sendTyping()"
            />
            <button
              type="submit"
              :disabled="!draft.trim()"
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy text-white disabled:opacity-40"
              :aria-label="C.send"
            >
              <Send class="h-4 w-4 -scale-x-100" />
            </button>
          </form>
        </template>
      </section>
    </Transition>

    <!-- Launcher -->
    <button
      class="relative flex h-14 w-14 items-center justify-center rounded-full bg-navy text-white shadow-luxury hover:opacity-90"
      :aria-label="C.launcher"
      :disabled="opening"
      @click="toggle"
    >
      <MessageCircle class="h-6 w-6" />
      <span
        v-if="chat.unread.value"
        class="absolute -top-1 -end-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-bold"
      >
        {{ chat.unread.value }}
      </span>
    </button>
  </div>
</template>

<style scoped>
.chat-pop-enter-active,
.chat-pop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.chat-pop-enter-from,
.chat-pop-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}
</style>
