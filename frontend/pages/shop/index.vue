<script setup lang="ts">
import { SlidersHorizontal, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio, Product } from '~/types'
import { toFa } from '~/utils/format'

// Storefront: full catalogue with add-to-cart (no online payment — the cart →
// order flow captures the order as a lead). Reuses the 'products' payload.
const { data: products, pending } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})

// Admin-curated collections shown as sections atop the catalogue.
const { data: portfolios } = await useFetch<Portfolio[]>('/portfolios', {
  baseURL: useApiBase(),
  key: 'portfolios',
  default: () => [],
})

const CATEGORIES = [
  { key: 'daily', label: CONTENT.products.daily.title },
  { key: 'lux_daily', label: CONTENT.products.lux_daily.title },
  { key: 'luxury', label: CONTENT.products.luxury.title },
] as const

// URL-synced filter state (shareable, survives reload + back/forward).
const { search, category, sort, weightMin, weightMax, ojratMin, ojratMax, karat, clear } =
  useShopFilters()

// Advanced filters live in a sheet (all viewports — 3 controls, no need to
// duplicate an inline desktop panel).
const filtersOpen = ref(false)

// Distinct karat values present (sorted). The control only shows when there's
// more than one — most items are 18k.
const karats = computed(() =>
  [...new Set((products.value || []).map((p) => p.karat).filter((k): k is number => k != null))]
    .sort((a, b) => a - b),
)

// Active-product count per category, for the category cards.
const categoryCounts = computed(() => {
  const c: Record<string, number> = { daily: 0, lux_daily: 0, luxury: 0 }
  for (const p of products.value || []) if (c[p.category] != null) c[p.category]++
  return c
})

// Count of active advanced-filter *groups*, for the filter button badge.
const advancedCount = computed(
  () =>
    (weightMin.value || weightMax.value ? 1 : 0) +
    (ojratMin.value || ojratMax.value ? 1 : 0) +
    (karat.value !== '' ? 1 : 0),
)
const hasFilters = computed(
  () => !!category.value || !!search.value.trim() || advancedCount.value > 0,
)
const categoryLabel = computed(() => CATEGORIES.find((c) => c.key === category.value)?.label)

const SORT_OPTIONS = [
  { value: 'newest', label: CONTENT.shop.sortNewest },
  { value: 'weight_asc', label: CONTENT.shop.sortWeightAsc },
  { value: 'weight_desc', label: CONTENT.shop.sortWeightDesc },
] as const

// A nullable numeric field passes only when present and inside any active bound.
function inRange(val: string | null, min: string, max: string) {
  if (!min && !max) return true
  if (val == null) return false
  const n = Number(val)
  if (min && n < Number(min)) return false
  if (max && n > Number(max)) return false
  return true
}

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  let list = (products.value || []).filter((p) => {
    if (category.value && p.category !== category.value) return false
    if (q && !p.name.toLowerCase().includes(q) && !p.sku.toLowerCase().includes(q)) return false
    if (!inRange(p.weight_grams, weightMin.value, weightMax.value)) return false
    if (!inRange(p.ojrat_percent, ojratMin.value, ojratMax.value)) return false
    if (karat.value !== '' && p.karat !== karat.value) return false
    return true
  })
  // Weight sorts: nulls (unknown weight) always sink to the end.
  const weight = (p: Product) => (p.weight_grams == null ? null : Number(p.weight_grams))
  if (sort.value === 'weight_asc' || sort.value === 'weight_desc') {
    const dir = sort.value === 'weight_asc' ? 1 : -1
    list = [...list].sort((a, b) => {
      const pa = weight(a); const pb = weight(b)
      if (pa == null) return 1
      if (pb == null) return -1
      return (pa - pb) * dir
    })
  } else {
    list = [...list].sort((a, b) => a.sort_order - b.sort_order)
  }
  return list
})

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
      <div class="relative aspect-[3/2] w-full overflow-hidden sm:aspect-[21/7]">
        <NuxtImg
          src="/shop-hero.jpg"
          :alt="CONTENT.shop.title"
          class="h-full w-full object-cover"
          width="1450"
          height="1000"
          format="webp"
          sizes="100vw"
          loading="eager"
          fetchpriority="high"
          preload
        />
        <div
          class="absolute inset-0 bg-gradient-to-t from-black/65 via-black/25 to-transparent"
          aria-hidden="true"
        />
        <div class="absolute inset-0 flex flex-col items-center justify-end px-5 pb-6 text-center sm:pb-12">
          <p class="mb-2 text-[11px] tracking-[0.3em] text-gold sm:text-sm">{{ CONTENT.shop.heroEyebrow }}</p>
          <h1 class="text-2xl font-medium text-white drop-shadow sm:text-5xl">{{ CONTENT.shop.title }}</h1>
          <p class="mt-3 hidden max-w-2xl text-sm leading-7 text-white/85 sm:block sm:text-base">
            {{ CONTENT.shop.description }}
          </p>
        </div>
      </div>
    </section>

    <div class="mx-auto max-w-content px-5 sm:px-10">
      <!-- Shop by category — the single category control (filter bar no longer duplicates it) -->
      <ShopCategories v-model="category" :counts="categoryCounts" />

      <!-- Admin-curated collections (hidden while the user is actively filtering) -->
      <PortfolioSection
        v-for="pf in portfolios"
        v-show="!hasFilters"
        :key="pf.id"
        :portfolio="pf"
      />

      <!-- Catalogue section anchor -->
      <SectionDivider :eyebrow="CONTENT.shop.catalogEyebrow" :title="CONTENT.shop.catalogTitle" />

      <!-- Filter toolbar: search · sort · advanced -->
      <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          v-model="search"
          type="search"
          :placeholder="CONTENT.shop.searchPlaceholder"
          class="form-control h-11 sm:max-w-xs"
          aria-label="جستجو"
        />
        <div class="flex items-center gap-3 sm:ms-auto">
          <!-- Sort segmented control -->
          <div class="corner-soft flex overflow-hidden border border-line" role="group" :aria-label="CONTENT.shop.sortLabel">
            <button
              v-for="(o, i) in SORT_OPTIONS"
              :key="o.value"
              type="button"
              class="h-11 whitespace-nowrap px-3 text-sm transition"
              :class="[
                sort === o.value ? 'bg-navy text-white' : 'text-ink-muted hover:text-ink',
                i > 0 ? 'border-s border-line' : '',
              ]"
              :aria-pressed="sort === o.value"
              @click="sort = o.value"
            >
              {{ o.label }}
            </button>
          </div>
          <!-- Advanced filters (opens sheet) -->
          <button
            type="button"
            class="flex h-11 shrink-0 items-center gap-2 border px-3 text-sm transition"
            :class="advancedCount ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
            @click="filtersOpen = true"
          >
            <SlidersHorizontal :size="16" aria-hidden="true" />
            {{ CONTENT.shop.advancedToggle }}
            <span
              v-if="advancedCount"
              class="tnum flex h-5 min-w-5 items-center justify-center rounded-full bg-gold px-1 text-[11px] font-bold text-navy-deep"
            >{{ toFa(advancedCount) }}</span>
          </button>
        </div>
      </div>

      <!-- Active-filter chips + clear-all -->
      <div v-if="hasFilters" class="mb-4 flex flex-wrap items-center gap-2">
        <button
          v-if="search.trim()"
          type="button"
          class="corner-soft inline-flex items-center gap-1 border border-line px-2 py-1 text-xs
            text-ink-muted transition hover:border-navy hover:text-ink"
          :aria-label="`${CONTENT.shop.clearFilters}: ${CONTENT.shop.searchChip(search.trim())}`"
          @click="search = ''"
        >
          {{ CONTENT.shop.searchChip(search.trim()) }}
          <X :size="13" aria-hidden="true" />
        </button>
        <button
          v-if="category"
          type="button"
          class="corner-soft inline-flex items-center gap-1 border border-line px-2 py-1 text-xs
            text-ink-muted transition hover:border-navy hover:text-ink"
          :aria-label="`${CONTENT.shop.clearFilters}: ${categoryLabel}`"
          @click="category = ''"
        >
          {{ categoryLabel }}
          <X :size="13" aria-hidden="true" />
        </button>
        <button
          v-if="weightMin || weightMax"
          type="button"
          class="corner-soft inline-flex items-center gap-1 border border-line px-2 py-1 text-xs
            text-ink-muted transition hover:border-navy hover:text-ink"
          @click="weightMin = ''; weightMax = ''"
        >
          {{ CONTENT.shop.weightChip(weightMin, weightMax) }}
          <X :size="13" aria-hidden="true" />
        </button>
        <button
          v-if="ojratMin || ojratMax"
          type="button"
          class="corner-soft inline-flex items-center gap-1 border border-line px-2 py-1 text-xs
            text-ink-muted transition hover:border-navy hover:text-ink"
          @click="ojratMin = ''; ojratMax = ''"
        >
          {{ CONTENT.shop.ojratChip(ojratMin, ojratMax) }}
          <X :size="13" aria-hidden="true" />
        </button>
        <button
          v-if="karat !== ''"
          type="button"
          class="corner-soft inline-flex items-center gap-1 border border-line px-2 py-1 text-xs
            text-ink-muted transition hover:border-navy hover:text-ink"
          @click="karat = ''"
        >
          {{ CONTENT.shop.karatChip(karat) }}
          <X :size="13" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="text-xs text-gold-text underline underline-offset-2 hover:no-underline"
          @click="clear"
        >
          {{ CONTENT.shop.clearAll }}
        </button>
      </div>

      <p class="mb-4 text-sm text-ink-muted" aria-live="polite">
        {{ CONTENT.shop.resultCount(filtered.length) }}
      </p>

      <!-- Loading skeletons (client-side navigations / refetch) -->
      <div v-if="pending && !filtered.length" class="grid grid-cols-2 gap-4 pb-16 sm:gap-6 lg:grid-cols-3 xl:grid-cols-4">
        <ProductCardSkeleton v-for="n in 8" :key="n" />
      </div>

      <div v-else-if="filtered.length" class="grid grid-cols-2 gap-4 pb-16 sm:gap-6 lg:grid-cols-3 xl:grid-cols-4">
        <ProductCard
          v-for="(p, i) in filtered"
          :key="p.id"
          :product="p"
          :index="i"
          shop
        />
      </div>

      <div v-else class="py-16 text-center">
        <p class="text-ink-muted">{{ CONTENT.shop.empty }}</p>
        <button
          v-if="hasFilters"
          type="button"
          class="corner-soft mt-4 border border-navy px-4 py-2 text-sm text-ink transition
            hover:bg-navy hover:text-white"
          @click="clear"
        >
          {{ CONTENT.shop.clearFilters }}
        </button>
      </div>
    </div>

    <!-- Advanced filters sheet (weight / اجرت / عیار) -->
    <BaseSheet v-model="filtersOpen" :title="CONTENT.shop.filtersTitle">
      <div class="space-y-6">
        <div class="flex flex-col gap-1.5">
          <span class="text-sm text-ink-muted">{{ CONTENT.shop.weightLabel }}</span>
          <div class="flex items-center gap-2">
            <input v-model="weightMin" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.minLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.weightLabel} ${CONTENT.shop.minLabel}`" />
            <span class="text-ink-muted">–</span>
            <input v-model="weightMax" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.maxLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.weightLabel} ${CONTENT.shop.maxLabel}`" />
          </div>
        </div>
        <div class="flex flex-col gap-1.5">
          <span class="text-sm text-ink-muted">{{ CONTENT.shop.ojratLabel }}</span>
          <div class="flex items-center gap-2">
            <input v-model="ojratMin" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.minLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.ojratLabel} ${CONTENT.shop.minLabel}`" />
            <span class="text-ink-muted">–</span>
            <input v-model="ojratMax" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.maxLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.ojratLabel} ${CONTENT.shop.maxLabel}`" />
          </div>
        </div>
        <div v-if="karats.length > 1" class="flex flex-col gap-1.5">
          <span class="text-sm text-ink-muted">{{ CONTENT.shop.karatLabel }}</span>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="h-11 border px-4 text-sm transition"
              :class="karat === '' ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
              @click="karat = ''"
            >
              {{ CONTENT.shop.all }}
            </button>
            <button
              v-for="k in karats"
              :key="k"
              type="button"
              class="tnum h-11 border px-4 text-sm transition"
              :class="karat === k ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
              @click="karat = k"
            >
              {{ toFa(k) }}
            </button>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center gap-3">
          <button
            v-if="advancedCount"
            type="button"
            class="h-12 border border-line px-4 text-sm text-ink-muted transition hover:border-navy hover:text-ink"
            @click="weightMin = ''; weightMax = ''; ojratMin = ''; ojratMax = ''; karat = ''"
          >
            {{ CONTENT.shop.clearAll }}
          </button>
          <button
            type="button"
            class="flex h-12 flex-1 items-center justify-center bg-navy text-base font-medium text-white transition hover:bg-gold"
            @click="filtersOpen = false"
          >
            {{ CONTENT.shop.applyFilters }}
          </button>
        </div>
      </template>
    </BaseSheet>
  </main>
</template>
