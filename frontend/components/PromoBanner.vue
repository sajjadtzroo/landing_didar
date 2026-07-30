<script setup lang="ts">
// Slim top promotion strip, fixed above the nav. Gold on navy so it reads as a
// distinct announcement band. Dismissible; the navs offset below it while open.
import { Sparkles, X } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

const { open } = usePromo()
const route = useRoute()

// Per-landing promo text (keyed by /l/<slug>); falls back to the default.
const text = computed(() => {
  const slug = route.params.slug
  return (typeof slug === 'string' && CONTENT.promoByLanding[slug]) || CONTENT.promo
})
</script>

<template>
  <Transition name="promo">
    <!-- White band: near-black (navy-deep) text = 19.8:1 contrast; gold sparkle 5.8:1. -->
    <div
      v-if="open"
      class="fixed inset-x-0 top-0 z-[70] flex min-h-12 items-center justify-center gap-2.5
        border-b border-line bg-white px-11 py-2.5 text-center text-xs font-semibold
        leading-snug text-navy-deep sm:text-base"
      role="status"
    >
      <Sparkles :size="17" class="hidden shrink-0 text-gold-text sm:block" aria-hidden="true" />
      <span>{{ text }}</span>
      <button
        type="button"
        class="absolute end-1 flex h-11 w-11 items-center justify-center text-navy-deep/60
          transition-colors hover:text-navy-deep"
        aria-label="بستن اعلان"
        @click="open = false"
      >
        <X :size="18" />
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.promo-enter-active,
.promo-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.promo-enter-from,
.promo-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .promo-enter-from,
  .promo-leave-to {
    transform: none;
  }
}
</style>
