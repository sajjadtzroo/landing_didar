<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio, Product } from '~/types'
import { toFa } from '~/utils/format'

// Storefront SHOWCASE: hero, live rate, trust, categories, collections and the
// top 10 pieces. The full filterable catalogue lives on /products — category
// tiles and the "view all" CTA link there (?cat=… is read by useShopFilters).
const { data: products, pending } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})

const { data: portfolios } = await useFetch<Portfolio[]>('/portfolios', {
  baseURL: useApiBase(),
  key: 'portfolios',
  default: () => [],
})

// Top 8 by the admin's sort order (the API already returns them sorted) —
// fills the grid evenly: 4 rows of 2 on mobile, 2 rows of 4 on desktop.
const SHOWCASE_COUNT = 8
const showcase = computed(() => (products.value || []).slice(0, SHOWCASE_COUNT))
const total = computed(() => (products.value || []).length)

// Active-product count per category, for the category cards.
const categoryCounts = computed(() => {
  const c: Record<string, number> = { daily: 0, lux_daily: 0, luxury: 0 }
  for (const p of products.value || []) if (c[p.category] != null) c[p.category]++
  return c
})

// Category tiles navigate to the catalogue pre-filtered (no local filtering here).
function goToCategory(key: string) {
  navigateTo(key ? { path: '/products', query: { cat: key } } : '/products')
}

// Showcase carousel paging — same RTL-aware trick as ProductGrid/CollectionCarousel:
// the app is dir=rtl, where scrollLeft grows negative toward later items.
const showcaseScroller = ref<HTMLElement | null>(null)
function pageShowcase(dir: 1 | -1) {
  const el = showcaseScroller.value
  if (!el) return
  const rtl = getComputedStyle(el).direction === 'rtl' ? -1 : 1
  el.scrollBy({ left: dir * rtl * el.clientWidth * 0.85, behavior: 'smooth' })
}

// Hero: brand campaign shots, slow crossfade. Static pre-optimized JPEGs (same
// no-IPX reasoning as before). First slide SSRs eager; rotation is client-only
// and skipped for prefers-reduced-motion.
const HERO_SLIDES = [
  '/shop-hero-1.jpg',
  '/shop-hero-2.jpg',
  '/shop-hero-3.jpg',
  '/shop-hero-4.jpg',
  '/shop-hero-5.jpg',
]
const heroIndex = ref(0)
let heroTimer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  heroTimer = setInterval(() => {
    heroIndex.value = (heroIndex.value + 1) % HERO_SLIDES.length
  }, 5000)
})
onUnmounted(() => clearInterval(heroTimer))

const canonical = `${useSiteUrl()}/shop`
useHead({
  title: `${CONTENT.shop.title} | ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: CONTENT.shop.description },
    { property: 'og:title', content: `${CONTENT.shop.title} | ${CONTENT.brand}` },
    { property: 'og:description', content: CONTENT.shop.description },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: canonical },
  ],
  link: [{ rel: 'canonical', href: canonical }],
})
</script>

<template>
  <main class="pt-16 sm:pt-28">
    <!-- Hero banner (full-bleed showroom image) -->
    <section class="mb-8 sm:mb-10">
      <!-- Mobile: shorter hero so the shopping surface starts near the fold -->
      <div class="relative aspect-[16/5] w-full overflow-hidden">
        <img
          v-for="(src, i) in HERO_SLIDES"
          :key="src"
          :src="src"
          :alt="i === 0 ? CONTENT.shop.title : ''"
          class="absolute inset-0 h-full w-full object-cover transition-opacity duration-1000"
          :class="i === heroIndex ? 'opacity-100' : 'opacity-0'"
          width="1280"
          height="400"
          :loading="i === 0 ? 'eager' : 'lazy'"
          :fetchpriority="i === 0 ? 'high' : 'auto'"
          :aria-hidden="i !== heroIndex"
        />
        <!-- Finished brand banners carry their own logo/copy, so no text overlay.
             Keep the h1 for SEO/a11y, visually hidden. -->
        <h1 class="sr-only">{{ CONTENT.shop.title }}</h1>
      </div>
    </section>

    <!-- flex-col so mobile can reorder: the showcase grid rises above the curated
         collections via CSS order; desktop keeps the editorial order. -->
    <div class="mx-auto flex max-w-content flex-col px-5 sm:px-10">
      <!-- نرخ روز: live 18k market rate (the anchor of every gold storefront) -->
      <GoldPriceStrip />

      <!-- Trust: authenticity (→ /verify), warranty, buyback -->
      <ShopTrust />

      <!-- Shop by category — tiles open the catalogue pre-filtered -->
      <ShopCategories :counts="categoryCounts" @update:model-value="goToCategory" />

      <!-- Admin-curated collections: ONE carousel (2 per view), every collection
           (eid, firooze, …) reachable in a swipe. -->
      <section class="order-2 sm:order-none">
        <CollectionCarousel :portfolios="portfolios" />
      </section>

      <section class="order-1 sm:order-none">
        <!-- Showcase: the top pieces + CTA into the full catalogue -->
        <SectionDivider :eyebrow="CONTENT.shop.catalogEyebrow" :title="CONTENT.shop.catalogTitle" />

        <div v-if="pending && !showcase.length" class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
          <ProductCardSkeleton v-for="n in 8" :key="n" />
        </div>

        <!-- Showcase carousel: full-bleed scroll-snap row, RTL-aware lg arrows
             (same pattern as ProductGrid / CollectionCarousel). -->
        <div v-else class="relative">
          <div
            ref="showcaseScroller"
            class="-mx-5 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-5 px-5 pb-2
              [scrollbar-width:none] sm:-mx-10 sm:gap-6 sm:scroll-px-10 sm:px-10
              [&::-webkit-scrollbar]:hidden"
          >
            <ProductCard
              v-for="(p, i) in showcase"
              :key="p.id"
              :product="p"
              :index="i"
              shop
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
            @click="pageShowcase(1)"
          >
            <ChevronLeft :size="20" />
          </button>
          <button
            type="button"
            class="absolute start-1 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center
              justify-center border border-line bg-surface/90 text-ink shadow-luxury backdrop-blur
              hover:text-gold-text lg:flex"
            aria-label="قبلی"
            @click="pageShowcase(-1)"
          >
            <ChevronRight :size="20" />
          </button>
        </div>

        <!-- CTA: the full catalogue (search, sort, filters) lives on /products -->
        <div class="mb-16 mt-8 flex justify-center">
          <NuxtLink
            to="/products"
            class="flex h-12 items-center gap-2 bg-navy px-8 text-sm font-medium text-white
              transition duration-300 hover:bg-gold"
          >
            {{ CONTENT.shop.viewAllProducts }}
            <span v-if="total > SHOWCASE_COUNT" class="tnum text-white/80">({{ toFa(total) }})</span>
            <ChevronLeft :size="16" class="rotate-180" aria-hidden="true" />
          </NuxtLink>
        </div>
      </section>
    </div>
  </main>
</template>
