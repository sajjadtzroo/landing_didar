<script setup lang="ts">
// First-load promo popup — mirrors PromoBanner's look (white card, navy-deep
// text, gold sparkle) with a CTA. Shows on every landing load; re-opens on
// client-side navigation between landings. No persistence, by design.
import { Sparkles, X } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import { CONTENT } from '~/constants/content'

const route = useRoute()
const open = ref(true)
const card = ref<HTMLElement | null>(null)

// Same per-landing resolver as PromoBanner.
const text = computed(() => {
  const slug = route.params.slug
  return (typeof slug === 'string' && CONTENT.promoByLanding[slug]) || CONTENT.promo
})

// Re-show whenever the landing slug changes (SPA nav counts as a "load").
watch(() => route.params.slug, () => (open.value = true))

watch(open, async (on) => {
  if (on) {
    await nextTick()
    card.value?.focus()
  }
})

function close() {
  open.value = false
}
function goToProducts() {
  close()
  document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })
}

useEventListener(document, 'keydown', (e: KeyboardEvent) => {
  if (e.key === 'Escape' && open.value) close()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="promo-pop">
      <div
        v-if="open"
        class="fixed inset-0 z-[80] flex items-center justify-center bg-navy-deep/60 p-5"
        @click.self="close"
      >
        <div
          ref="card"
          tabindex="-1"
          role="dialog"
          aria-modal="true"
          :aria-label="text"
          class="relative w-full max-w-md border border-line bg-white px-6 py-8 text-center
            text-navy-deep shadow-luxury outline-none"
        >
          <button
            type="button"
            class="absolute end-1 top-1 flex h-11 w-11 items-center justify-center
              text-navy-deep/60 transition-colors hover:text-navy-deep"
            aria-label="بستن اعلان"
            @click="close"
          >
            <X :size="18" />
          </button>

          <Sparkles :size="28" class="mx-auto mb-4 text-gold-text" aria-hidden="true" />
          <p class="text-base font-semibold leading-relaxed sm:text-lg">{{ text }}</p>

          <button
            type="button"
            class="mt-6 inline-flex h-[52px] w-full items-center justify-center bg-navy
              text-base font-medium text-white transition-colors duration-300 hover:bg-gold"
            @click="goToProducts"
          >
            {{ CONTENT.hero.cta }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.promo-pop-enter-active,
.promo-pop-leave-active {
  transition: opacity 0.25s ease;
}
.promo-pop-enter-active > div,
.promo-pop-leave-active > div {
  transition: transform 0.25s ease;
}
.promo-pop-enter-from,
.promo-pop-leave-to {
  opacity: 0;
}
.promo-pop-enter-from > div,
.promo-pop-leave-to > div {
  transform: translateY(12px);
}
@media (prefers-reduced-motion: reduce) {
  .promo-pop-enter-from > div,
  .promo-pop-leave-to > div {
    transform: none;
  }
}
</style>
