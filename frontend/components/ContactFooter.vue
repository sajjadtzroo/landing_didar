<script setup lang="ts">
import { Clock, Instagram, MapPin, MessageCircle, Phone, Send } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

const { trackEvent, trackGoal } = useAnalytics()
const { public: cfg } = useRuntimeConfig()

const social = [
  { href: CONTENT.whatsapp, label: 'WhatsApp', icon: MessageCircle },
  { href: CONTENT.telegram, label: 'Telegram', icon: Send },
  { href: CONTENT.instagram, label: 'Instagram', icon: Instagram },
]

function onCall() {
  trackEvent('contact', 'phone_click', 'footer')
  trackGoal(Number(cfg.matomoGoalPhone))
}
</script>

<template>
  <footer class="border-t border-gold/25 bg-footer text-cream">
    <!-- text-right anchors every column to the RTL leading edge; icons lead each
         row as the first flex child so they sit on the right, not the left. -->
    <div class="mx-auto grid max-w-content gap-x-8 gap-y-10 px-6 py-16 text-right sm:grid-cols-3 sm:px-10">
      <!-- Brand + contact -->
      <div>
        <div class="flex justify-end">
          <BrandLogo :height="40" />
        </div>
        <p class="mt-2 max-w-xs text-sm leading-relaxed text-cream/60">
          {{ CONTENT.footer.tagline }}
        </p>
        <a
          :href="`tel:${CONTENT.phone}`"
          class="mt-5 inline-flex items-center gap-2 text-cream/85 transition-colors hover:text-gold-soft"
          @click="onCall"
        >
          <Phone :size="18" class="shrink-0 text-gold-soft" />
          <span class="tnum" dir="ltr">{{ CONTENT.phoneDisplay }}</span>
        </a>
      </div>

      <!-- Address + hours -->
      <div>
        <h2 class="text-sm font-medium text-gold-soft">{{ CONTENT.footer.hoursTitle }}</h2>
        <ul class="mt-4 space-y-3 text-sm text-cream/75">
          <li class="flex items-center gap-2">
            <MapPin :size="18" class="shrink-0 text-gold-soft" />
            <span>{{ CONTENT.footer.address }}</span>
          </li>
          <li class="flex items-center gap-2">
            <Clock :size="18" class="shrink-0 text-gold-soft" />
            <span>{{ CONTENT.footer.hours }}</span>
          </li>
        </ul>
      </div>

      <!-- Social -->
      <div>
        <h2 class="text-sm font-medium text-gold-soft">{{ CONTENT.footer.socialTitle }}</h2>
        <div class="mt-4 flex gap-3">
          <a
            v-for="s in social"
            :key="s.label"
            :href="s.href"
            target="_blank"
            rel="noopener"
            :aria-label="s.label"
            class="flex h-11 w-11 items-center justify-center border border-gold/40 text-cream transition-colors hover:border-gold hover:bg-gold hover:text-navy"
          >
            <component :is="s.icon" :size="20" />
          </a>
        </div>
      </div>
    </div>

    <!-- Bottom bar: gold hairline + copyright -->
    <div class="mx-auto max-w-content px-6 sm:px-10">
      <p class="border-t border-gold/15 py-6 text-center text-xs text-cream/50">
        © {{ toFa(1404) }} — {{ CONTENT.footer.rights }}
      </p>
    </div>
  </footer>
</template>
