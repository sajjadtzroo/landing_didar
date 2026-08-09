<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{ modelValue: boolean; title?: string }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const panel = ref<HTMLElement | null>(null)
let lastFocused: HTMLElement | null = null

const { offset, dragging, down, move, up, reset } = useDragDismiss(() =>
  emit('update:modelValue', false),
)

const panelStyle = computed(() => ({
  transform: `translateY(${offset.value}px)`,
  transition: dragging.value ? 'none' : 'transform 0.3s cubic-bezier(0.2,0,0,1)',
}))

function close() {
  emit('update:modelValue', false)
}

// Focus trap: keep Tab within the panel; Esc closes.
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
    return
  }
  if (e.key !== 'Tab' || !panel.value) return
  const nodes = panel.value.querySelectorAll<HTMLElement>(
    'a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])',
  )
  if (!nodes.length) return
  const first = nodes[0]
  const last = nodes[nodes.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (import.meta.server) return
    if (open) {
      lastFocused = document.activeElement as HTMLElement
      document.body.style.overflow = 'hidden'
      reset()
      await nextTick()
      panel.value?.focus()
    } else {
      document.body.style.overflow = ''
      lastFocused?.focus() // return focus to the trigger
    }
  },
)
</script>

<template>
  <ClientOnly>
    <Teleport to="body">
      <Transition name="sheet">
        <div
          v-if="modelValue"
          class="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
          @keydown="onKeydown"
        >
          <!-- Scrim: 40–60% for foreground legibility. Tap to dismiss. -->
          <div
            class="absolute inset-0 bg-navy-deep/60"
            @click="close"
            aria-hidden="true"
          />
          <div
            ref="panel"
            role="dialog"
            aria-modal="true"
            :aria-label="title"
            tabindex="-1"
            :style="panelStyle"
            class="relative flex max-h-[90vh] w-full flex-col bg-surface-raised
              shadow-luxury outline-none sm:max-w-lg"
          >
            <!-- Drag handle: 1:1 tracking dismiss (§2b) -->
            <div
              class="flex shrink-0 cursor-grab touch-none items-center justify-between
                border-b border-line px-5 py-4"
              @pointerdown="down"
              @pointermove="move"
              @pointerup="up"
              @pointercancel="up"
            >
              <div
                class="absolute inset-x-0 top-2 mx-auto h-1 w-10 rounded-full bg-line
                  sm:hidden"
                aria-hidden="true"
              />
              <h2 v-if="title" class="text-lg font-medium text-ink">{{ title }}</h2>
              <button
                type="button"
                class="ms-auto flex h-11 w-11 items-center justify-center text-ink-muted
                  hover:text-gold-text"
                :aria-label="'بستن'"
                @pointerdown.stop
                @click="close"
              >
                <X :size="22" />
              </button>
            </div>

            <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
              <slot />
            </div>

            <div v-if="$slots.footer" class="shrink-0 border-t border-line p-5">
              <slot name="footer" />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </ClientOnly>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.3s ease;
}
.sheet-enter-active [role='dialog'],
.sheet-leave-active [role='dialog'] {
  transition: transform 0.3s cubic-bezier(0.2, 0, 0, 1);
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-from [role='dialog'],
.sheet-leave-to [role='dialog'] {
  transform: translateY(100%);
}
@media (prefers-reduced-motion: reduce) {
  .sheet-enter-from [role='dialog'],
  .sheet-leave-to [role='dialog'] {
    transform: none;
  }
}
</style>
