<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'

// Heading/anchor are props so the landing can render one grid per category.
// Defaults preserve the /products catalogue page (single grid) untouched.
withDefaults(
  defineProps<{
    products: Product[]
    carousel?: boolean
    eyebrow?: string
    title?: string
    description?: string
    anchorId?: string
    flush?: boolean // stacked carousel: continue the previous section's band
    // Route for the closing "view all products" CTA (spec: outline treatment,
    // navigational <NuxtLink>, prefetched on viewport entry — NuxtLink default).
    viewAllTo?: string
  }>(),
  {
    eyebrow: () => CONTENT.products.eyebrow,
    title: () => CONTENT.products.title,
    description: () => CONTENT.products.description,
    anchorId: 'products',
    viewAllTo: undefined, // no CTA unless a route is given
  },
)

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
    :id="anchorId"
    ref="section"
    :class="flush
      ? 'bg-cream-deep pb-16 pt-6'
      : 'bg-gradient-to-b from-cream-bright via-cream to-cream-deep py-16'"
  >
    <div class="mx-auto max-w-content px-5 sm:px-10">
      <SectionDivider
        :eyebrow="eyebrow"
        :title="title"
        :description="description"
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
        <!-- Left edge fade: extends to the true viewport edge (the scroller
             bleeds -mx-5/-mx-10) so the peeking card fully melts into the bg. -->
        <div
          class="pointer-events-none absolute inset-y-0 -left-5 z-10 w-24
            bg-gradient-to-r from-cream via-cream/90 to-transparent sm:-left-10 sm:w-36"
          aria-hidden="true"
        />
        <!-- RTL: arrows point outward. Left (inline-end) = next ‹ ; right
             (inline-start) = previous › . The left one sits above the fade. -->
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
    </div>

    <!-- Closing CTA: browse the whole catalogue. Outline = never competes with
         the per-card add-to-cart primary. -->
    <div v-if="viewAllTo" class="mt-10 px-5 text-center sm:px-10">
      <NuxtLink
        :to="viewAllTo"
        class="inline-flex h-12 w-full max-w-md items-center justify-center gap-2 border
          border-navy text-sm font-medium text-ink transition duration-300
          hover:bg-navy hover:text-white sm:w-auto sm:px-10"
      >
        {{ CONTENT.shop.viewAllProducts }}
        <ChevronLeft :size="16" aria-hidden="true" />
      </NuxtLink>
    </div>
  </section>
</template>
