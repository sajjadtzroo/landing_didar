<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'

defineProps<{ products: Product[]; carousel?: boolean }>()

const { trackEvent } = useAnalytics()

// Carousel paging. dir=1 advances to the NEXT card. ponytail: the app is
// dir=rtl, where scrollLeft grows negative toward later items — the direction
// check keeps it correct in both RTL and LTR.
const scroller = ref<HTMLElement | null>(null)
function page(dir: 1 | -1) {
  const el = scroller.value
  if (!el) return
  const rtl = getComputedStyle(el).direction === 'rtl' ? -1 : 1
  el.scrollBy({ left: dir * rtl * el.clientWidth * 0.85, behavior: 'smooth' })
}

// products.view_list — fires when the grid enters the viewport.
const section = ref<HTMLElement | null>(null)
let fired = false
if (import.meta.client) {
  useIntersectionObserver(section, ([entry]) => {
    if (entry?.isIntersecting && !fired) {
      fired = true
      trackEvent('products', 'view_list')
    }
  })
}
</script>

<template>
  <section
    id="products"
    ref="section"
    class="bg-gradient-to-b from-cream-bright via-cream to-[#EFE6D6] py-16"
  >
    <div class="mx-auto max-w-content px-5 sm:px-10">
      <SectionDivider
        :eyebrow="CONTENT.products.eyebrow"
        :title="CONTENT.products.title"
        :description="CONTENT.products.description"
      />
      <!-- Grid (default) -->
      <div v-if="!carousel" class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
        <ProductCard
          v-for="(product, i) in products"
          :key="product.id"
          :product="product"
          :index="i"
        />
      </div>

      <!-- Carousel (landing showcase): full-bleed scroll-snap row + lg arrows -->
      <div v-else class="relative">
        <div
          ref="scroller"
          class="-mx-5 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-5 px-5 pb-2
            [scrollbar-width:none] sm:-mx-10 sm:gap-6 sm:scroll-px-10 sm:px-10
            [&::-webkit-scrollbar]:hidden"
        >
          <ProductCard
            v-for="(product, i) in products"
            :key="product.id"
            :product="product"
            :index="i"
            class="snap-start shrink-0 basis-[72%] sm:basis-[46%] lg:basis-[31%]"
          />
        </div>
        <button
          type="button"
          class="absolute end-1 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center
            justify-center border border-line bg-surface/90 text-ink shadow-luxury backdrop-blur
            hover:text-gold-text lg:flex"
          aria-label="قبلی"
          @click="page(-1)"
        >
          <ChevronRight :size="20" />
        </button>
        <button
          type="button"
          class="absolute start-1 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center
            justify-center border border-line bg-surface/90 text-ink shadow-luxury backdrop-blur
            hover:text-gold-text lg:flex"
          aria-label="بعدی"
          @click="page(1)"
        >
          <ChevronLeft :size="20" />
        </button>
      </div>
    </div>
  </section>
</template>
