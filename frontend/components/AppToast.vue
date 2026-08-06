<script setup lang="ts">
// Global toast host. aria-live="polite" so screen readers announce without
// stealing focus. Sits above the bottom nav/fabs on mobile.
import { X } from 'lucide-vue-next'

const { toasts, dismiss } = useToast()
</script>

<template>
  <ClientOnly>
    <div
      class="pointer-events-none fixed inset-x-0 bottom-28 z-[60] flex flex-col items-center gap-2
        px-4 sm:bottom-8"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-center gap-3 border border-white/10 bg-navy px-4 py-3
            text-sm text-cream shadow-luxury"
        >
          <span>{{ t.message }}</span>
          <button
            type="button"
            class="text-cream/70 transition hover:text-cream"
            :aria-label="'بستن'"
            @click="dismiss(t.id)"
          >
            <X :size="16" aria-hidden="true" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </ClientOnly>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.2, 0, 0, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
@media (prefers-reduced-motion: reduce) {
  .toast-enter-from,
  .toast-leave-to {
    transform: none;
  }
}
</style>
