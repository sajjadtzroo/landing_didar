<script setup lang="ts">
import { SlidersHorizontal, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio, Product } from '~/types'
import { toFa } from '~/utils/format'

// The FULL catalogue: search / sort / category / collection / advanced filters.
// /shop is the showcase (top 10 + CTA here); this page is where browsing lives.
// Same payload keys as /shop so Nuxt reuses the cached responses.
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

const CATEGORIES = [
  { key: 'daily', label: CONTENT.products.daily.title },
  { key: 'lux_daily', label: CONTENT.products.lux_daily.title },
  { key: 'luxury', label: CONTENT.products.luxury.title },
  { key: 'watch', label: CONTENT.products.watch.title },
] as const

// URL-synced filter state (shareable; /shop links in with ?cat=…).
const { search, category, collection, sort, weightMin, weightMax, ojratMin, ojratMax, karat, clear } =
  useShopFilters()

const filtersOpen = ref(false)

const karats = computed(() =>
  [...new Set((products.value || []).map((p) => p.karat).filter((k): k is number => k != null))]
    .sort((a, b) => a - b),
)

// Collection (= portfolio) filter options with live facet counts.
const collectionOptions = computed(() => {
  return (portfolios.value || []).map((pf) => {
    const ids = new Set<string>()
    for (const g of pf.groups) for (const pr of g.products) ids.add(pr.id)
    return { slug: pf.slug, name: pf.name, count: ids.size, ids }
  })
})
const collectionIds = computed(
  () => collectionOptions.value.find((c) => c.slug === collection.value)?.ids ?? null,
)
const collectionLabel = computed(
  () => collectionOptions.value.find((c) => c.slug === collection.value)?.name,
)

const karatCounts = computed(() => {
  const c: Record<number, number> = {}
  for (const p of products.value || []) if (p.karat != null) c[p.karat] = (c[p.karat] || 0) + 1
  return c
})

const advancedCount = computed(
  () =>
    (collection.value ? 1 : 0) +
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
    if (collectionIds.value && !collectionIds.value.has(p.id)) return false
    if (q && !p.name.toLowerCase().includes(q) && !p.sku.toLowerCase().includes(q)) return false
    if (!inRange(p.weight_grams, weightMin.value, weightMax.value)) return false
    if (!inRange(p.ojrat_percent, ojratMin.value, ojratMax.value)) return false
    if (karat.value !== '' && p.karat !== karat.value) return false
    return true
  })
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

const canonical = `${useSiteUrl()}/products`
useHead({
  title: `${CONTENT.shop.catalogTitle} | ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: CONTENT.products.description },
    { property: 'og:title', content: `${CONTENT.shop.catalogTitle} | ${CONTENT.brand}` },
    { property: 'og:description', content: CONTENT.products.description },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: canonical },
  ],
  link: [{ rel: 'canonical', href: canonical }],
})
</script>

<template>
  <main class="pt-16 sm:pt-28">
    <div class="mx-auto max-w-content px-5 sm:px-10">
      <!-- Header -->
      <header class="mb-6">
        <p class="mb-1 text-xs tracking-[0.2em] text-gold-text">{{ CONTENT.shop.catalogEyebrow }}</p>
        <h1 class="text-2xl font-medium text-ink sm:text-4xl">{{ CONTENT.shop.catalogTitle }}</h1>
      </header>

      <!-- نرخ روز: the anchor number stays visible while choosing pieces -->
      <GoldPriceStrip />

      <!-- Filter toolbar: search · sort · advanced (sheet on <lg) -->
      <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          v-model="search"
          type="search"
          :placeholder="CONTENT.shop.searchPlaceholder"
          class="form-control h-11 sm:max-w-xs"
          aria-label="جستجو"
        />
        <div class="flex items-center gap-3 sm:ms-auto">
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
          <button
            type="button"
            class="flex h-11 shrink-0 items-center gap-2 border px-3 text-sm transition lg:hidden"
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

      <!-- Category chips (the /shop tiles link here with ?cat=…) -->
      <div class="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="h-9 border px-3 text-sm transition"
          :class="category === '' ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
          @click="category = ''"
        >
          {{ CONTENT.shop.all }}
        </button>
        <button
          v-for="c in CATEGORIES"
          :key="c.key"
          type="button"
          class="h-9 border px-3 text-sm transition"
          :class="category === c.key ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
          :aria-pressed="category === c.key"
          @click="category = c.key"
        >
          {{ c.label }}
        </button>
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
          v-if="collection"
          type="button"
          class="corner-soft inline-flex items-center gap-1 border border-line px-2 py-1 text-xs
            text-ink-muted transition hover:border-navy hover:text-ink"
          :aria-label="`${CONTENT.shop.clearFilters}: ${collectionLabel}`"
          @click="collection = ''"
        >
          {{ collectionLabel }}
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

      <!-- Desktop: sticky filter sidebar (RTL: first column = right) + results. -->
      <div class="lg:grid lg:grid-cols-[16rem_minmax(0,1fr)] lg:items-start lg:gap-8">
        <aside class="hidden lg:block" aria-label="فیلترها">
          <div class="corner-soft sticky top-28 max-h-[calc(100dvh-8rem)] overflow-y-auto border border-line bg-surface-raised p-5">
            <h2 class="mb-5 text-base font-medium">{{ CONTENT.shop.filtersTitle }}</h2>
            <ShopFilterGroups
              v-model:collection="collection"
              v-model:weight-min="weightMin"
              v-model:weight-max="weightMax"
              v-model:ojrat-min="ojratMin"
              v-model:ojrat-max="ojratMax"
              v-model:karat="karat"
              :collections="collectionOptions"
              :karats="karats"
              :karat-counts="karatCounts"
            />
          </div>
        </aside>

        <div>
          <p class="mb-4 text-sm text-ink-muted" aria-live="polite">
            {{ CONTENT.shop.resultCount(filtered.length) }}
          </p>

          <div v-if="pending && !filtered.length" class="grid grid-cols-2 gap-4 pb-16 sm:gap-6 lg:grid-cols-2 xl:grid-cols-3">
            <ProductCardSkeleton v-for="n in 8" :key="n" />
          </div>

          <div v-else-if="filtered.length" class="grid grid-cols-2 gap-4 pb-16 sm:gap-6 lg:grid-cols-2 xl:grid-cols-3">
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
      </div>
    </div>

    <!-- Advanced filters sheet (<lg) -->
    <BaseSheet v-model="filtersOpen" :title="CONTENT.shop.filtersTitle">
      <ShopFilterGroups
        v-model:collection="collection"
        v-model:weight-min="weightMin"
        v-model:weight-max="weightMax"
        v-model:ojrat-min="ojratMin"
        v-model:ojrat-max="ojratMax"
        v-model:karat="karat"
        :collections="collectionOptions"
        :karats="karats"
        :karat-counts="karatCounts"
      />

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
