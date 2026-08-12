<script setup lang="ts">
// Scroll-snap product row with RTL-aware paging arrows + edge fade — the one
// carousel used by the /shop showcase and best-sellers sections. (ProductGrid
// keeps its own copy for the landing band; unify if a fourth variant appears.)
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { ref } from 'vue'
import type { Product } from '~/types'

defineProps<{ products: Product[]; shop?: boolean }>()

// dir=rtl: scrollLeft grows negative toward later items — sign-flip keeps
// dir=1 meaning "next card" in both directions.
const scroller = ref<HTMLElement | null>(null)
function page(dir: 1 | -1) {
  const el = scroller.value
  if (!el) return
  const rtl = getComputedStyle(el).direction === 'rtl' ? -1 : 1
  el.scrollBy({ left: dir * rtl * el.clientWidth * 0.85, behavior: 'smooth' })
}
</script>

<template>
  <div class="relative">
    <div
      ref="scroller"
      class="-mx-5 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-5 px-5 pb-2
        [scrollbar-width:none] sm:-mx-10 sm:gap-6 sm:scroll-px-10 sm:px-10
        [&::-webkit-scrollbar]:hidden"
    >
      <ProductCard
        v-for="(p, i) in products"
        :key="p.id"
        :product="p"
        :index="i"
        :shop="shop"
        class="snap-start shrink-0 basis-[72%] sm:basis-[46%] lg:basis-[24%]"
      />
    </div>
    <!-- Left edge fade over the peeking card (scroller bleeds -mx). -->
    <div
      class="pointer-events-none absolute inset-y-0 -left-5 z-10 w-24
        bg-gradient-to-r from-cream via-cream/90 to-transparent sm:-left-10 sm:w-36"
      aria-hidden="true"
    />
    <!-- RTL: left (inline-end) = next ‹ ; right (inline-start) = previous › -->
    <button
      type="button"
      class="absolute end-1 top-1/2 z-20 hidden h-11 w-11 -translate-y-1/2 items-center
        justify-center border border-line bg-surface/90 text-ink shadow-luxury backdrop-blur
        hover:text-gold-text lg:flex"
      aria-label="بعدی"
      @click="page(1)"
    >
      <ChevronLeft :size="20" />
    </button>
    <button
      type="button"
      class="absolute start-1 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center
        justify-center border border-line bg-surface/90 text-ink shadow-luxury backdrop-blur
        hover:text-gold-text lg:flex"
      aria-label="قبلی"
      @click="page(-1)"
    >
      <ChevronRight :size="20" />
    </button>
  </div>
</template>
