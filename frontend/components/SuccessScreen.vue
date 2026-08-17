<script setup lang="ts">
import { CheckCircle2, Phone, ShoppingBag, X } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'

defineProps<{ reference: string }>()

const { trackEvent, trackGoal } = useAnalytics()
const { closeSuccess } = useUiState()
const { public: cfg } = useRuntimeConfig()

function onCall() {
  trackEvent('contact', 'phone_click', 'success_screen')
  trackGoal(Number(cfg.matomoGoalPhone))
}

function backToShop() {
  closeSuccess()
  navigateTo('/shop')
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-surface px-6 text-center">
    <!-- Close (minimize): dismiss the overlay, stay on the current page -->
    <button
      type="button"
      class="absolute end-4 top-4 flex h-11 w-11 items-center justify-center rounded-full
        text-ink-muted transition-colors hover:text-ink"
      :aria-label="CONTENT.success.close"
      @click="closeSuccess"
    >
      <X :size="22" />
    </button>

    <CheckCircle2 :size="64" class="text-success" />
    <h2 class="mt-6 text-3xl font-medium text-ink">{{ CONTENT.success.title }}</h2>
    <p class="mt-4 text-sm text-ink-muted">{{ CONTENT.success.reference }}</p>
    <p class="tnum mt-1 text-2xl font-bold tracking-widest text-gold-text" dir="ltr">
      {{ reference }}
    </p>
    <p class="mt-6 max-w-sm text-base leading-8 text-ink-muted">{{ CONTENT.success.next }}</p>

    <div class="mt-8 flex flex-col items-center gap-3 sm:flex-row">
      <a
        :href="`tel:${CONTENT.phone}`"
        class="inline-flex h-[58px] w-[220px] items-center justify-center gap-2 bg-navy
          text-base font-medium text-white transition duration-300 hover:bg-gold"
        @click="onCall"
      >
        <Phone :size="18" />
        {{ CONTENT.success.call }}
      </a>
      <button
        type="button"
        class="inline-flex h-[58px] w-[220px] items-center justify-center gap-2 border border-line
          bg-surface text-base font-medium text-ink transition duration-300 hover:border-navy"
        @click="backToShop"
      >
        <ShoppingBag :size="18" />
        {{ CONTENT.success.backToShop }}
      </button>
    </div>
  </div>
</template>
