<script setup lang="ts">
import { CheckCircle2, Phone } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'

defineProps<{ reference: string }>()

const { trackEvent, trackGoal } = useAnalytics()
const { public: cfg } = useRuntimeConfig()

function onCall() {
  trackEvent('contact', 'phone_click', 'success_screen')
  trackGoal(Number(cfg.matomoGoalPhone))
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-surface px-6 text-center">
    <CheckCircle2 :size="64" class="text-success" />
    <h2 class="mt-6 text-3xl font-medium text-ink">{{ CONTENT.success.title }}</h2>
    <p class="mt-4 text-sm text-ink-muted">{{ CONTENT.success.reference }}</p>
    <p class="tnum mt-1 text-2xl font-bold tracking-widest text-gold-text" dir="ltr">
      {{ reference }}
    </p>
    <p class="mt-6 max-w-sm text-base leading-8 text-ink-muted">{{ CONTENT.success.next }}</p>
    <a
      :href="`tel:${CONTENT.phone}`"
      class="mt-8 inline-flex h-[58px] w-[220px] items-center justify-center gap-2 bg-navy
        text-base font-medium text-white transition duration-300 hover:bg-gold"
      @click="onCall"
    >
      <Phone :size="18" />
      {{ CONTENT.success.call }}
    </a>
  </div>
</template>
