<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'

// Storefront: full catalogue with prices + add-to-cart (no online payment — the
// cart → order flow captures the order as a lead). Reuses the 'products' payload.
const { data: products } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})

const CATEGORIES = [
  { key: 'daily', label: CONTENT.products.daily.title },
  { key: 'lux_daily', label: CONTENT.products.lux_daily.title },
  { key: 'luxury', label: CONTENT.products.luxury.title },
] as const

const search = ref('')
const category = ref<string>('') // '' = all
const sort = ref<'newest' | 'price_asc' | 'price_desc'>('newest')

const hasFilters = computed(() => !!category.value || !!search.value.trim())
const categoryLabel = computed(
  () => CATEGORIES.find((c) => c.key === category.value)?.label,
)
function clearFilters() {
  search.value = ''
  category.value = ''
}

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  let list = (products.value || []).filter((p) => {
    if (category.value && p.category !== category.value) return false
    if (q && !p.name.toLowerCase().includes(q) && !p.sku.toLowerCase().includes(q)) return false
    return true
  })
  // Price sorts: nulls ("on request") always sink to the end.
  const price = (p: Product) => (p.price == null ? null : Number(p.price))
  if (sort.value === 'price_asc' || sort.value === 'price_desc') {
    const dir = sort.value === 'price_asc' ? 1 : -1
    list = [...list].sort((a, b) => {
      const pa = price(a); const pb = price(b)
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
  <main class="pt-32 sm:pt-28">
    <div class="mx-auto max-w-content px-5 sm:px-10">
      <header class="mb-8">
        <h1 class="text-3xl font-medium text-ink sm:text-4xl">{{ CONTENT.shop.title }}</h1>
        <p class="mt-3 max-w-2xl text-pretty text-base leading-8 text-ink-muted">
          {{ CONTENT.shop.description }}
        </p>
      </header>

      <!-- Filter bar -->
      <div class="mb-6 flex flex-col gap-4 border-y border-line py-4 sm:flex-row sm:items-center">
        <input
          v-model="search"
          type="search"
          :placeholder="CONTENT.shop.searchPlaceholder"
          class="form-control sm:max-w-xs"
          aria-label="جستجو"
        />
        <div class="flex flex-wrap items-center gap-2">
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
            @click="category = c.key"
          >
            {{ c.label }}
          </button>
        </div>
        <label class="flex items-center gap-2 text-sm text-ink-muted sm:ms-auto">
          {{ CONTENT.shop.sortLabel }}
          <select v-model="sort" class="form-control h-9 w-auto py-0">
            <option value="newest">{{ CONTENT.shop.sortNewest }}</option>
            <option value="price_asc">{{ CONTENT.shop.sortPriceAsc }}</option>
            <option value="price_desc">{{ CONTENT.shop.sortPriceDesc }}</option>
          </select>
        </label>
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
          type="button"
          class="text-xs text-gold-text underline underline-offset-2 hover:no-underline"
          @click="clearFilters"
        >
          {{ CONTENT.shop.clearAll }}
        </button>
      </div>

      <p class="mb-4 text-sm text-ink-muted" aria-live="polite">
        {{ CONTENT.shop.resultCount(filtered.length) }}
      </p>

      <div v-if="filtered.length" class="grid grid-cols-2 gap-4 pb-16 sm:gap-6 lg:grid-cols-4">
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
          @click="clearFilters"
        >
          {{ CONTENT.shop.clearFilters }}
        </button>
      </div>
    </div>
  </main>
</template>
