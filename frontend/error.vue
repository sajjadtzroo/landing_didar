<script setup lang="ts">
import type { NuxtError } from '#app'
import { CONTENT } from '~/constants/content'
import { errorCopy } from '~/utils/errorCopy'
import { toFa } from '~/utils/format'

// App-level error page: every 4xx/5xx a visitor can hit gets branded, RTL
// Persian copy instead of Nuxt's default screen. Always-navy like the login
// screen (theme-independent — an error page must never depend on app state).
const props = defineProps<{ error: NuxtError }>()

const code = computed(() => props.error?.statusCode ?? 500)
const copy = computed(() => errorCopy(code.value))

useHead({
  title: `${copy.value.title} — دیدار گلد`,
  meta: [{ name: 'robots', content: 'noindex' }],
})

const isDev = import.meta.dev

const goShop = () => clearError({ redirect: '/shop' })
const retry = () => {
  window.location.reload()
}
</script>

<template>
  <div
    dir="rtl"
    class="min-h-screen flex flex-col items-center justify-center gap-6 bg-gradient-to-b from-navy to-navy-deep px-6 py-16 text-center"
  >
    <BrandLogo :height="34" />

    <p class="mt-4 text-7xl font-light tracking-widest text-gold" aria-hidden="true">
      {{ toFa(code) }}
    </p>

    <div class="h-px w-16 bg-gold/40" aria-hidden="true" />

    <h1 class="text-2xl font-medium text-cream">{{ copy.title }}</h1>
    <p class="max-w-sm leading-7 text-cream/70">{{ copy.message }}</p>

    <div class="mt-4 flex flex-wrap items-center justify-center gap-3">
      <button
        type="button"
        class="h-12 rounded-full bg-gold px-8 font-medium text-navy transition hover:brightness-110"
        @click="goShop"
      >
        بازگشت به فروشگاه
      </button>
      <button
        v-if="copy.retry"
        type="button"
        class="h-12 rounded-full border border-cream/30 px-8 text-cream transition hover:border-cream/60"
        @click="retry"
      >
        تلاش دوباره
      </button>
    </div>

    <a
      :href="`tel:${CONTENT.phone}`"
      class="mt-2 text-sm text-cream/50 transition hover:text-gold-soft"
      dir="ltr"
    >
      پشتیبانی: {{ CONTENT.phoneDisplay }}
    </a>

    <!-- Dev-only diagnostics; production builds never render the stack. -->
    <pre
      v-if="isDev && props.error?.message"
      class="mt-6 max-w-2xl overflow-x-auto rounded-lg bg-navy-deep p-4 text-start text-xs text-cream/60"
      dir="ltr"
      >{{ props.error.message }}</pre
    >
  </div>
</template>
