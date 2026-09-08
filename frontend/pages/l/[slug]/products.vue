<script setup lang="ts">
import { House } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Landing, Product } from '~/types'

const route = useRoute()
const slug = route.params.slug as string
const base = useApiBase()

// Reuse the landing fetch — same key as index.vue so Nuxt serves it from cache.
const { data: landing, error } = await useFetch<Landing>(`/landings/${slug}`, {
  baseURL: base,
  key: `landing-${slug}`,
})
if (error.value || !landing.value) {
  throw createError({ statusCode: 404, statusMessage: 'Landing not found', fatal: true })
}

// Flatten all groups into a single deduped product list (preserving group order).
const products = computed<Product[]>(() => {
  const seen = new Set<string>()
  const out: Product[] = []
  for (const g of landing.value?.groups || []) {
    for (const p of g.products) {
      if (!seen.has(p.id)) { seen.add(p.id); out.push(p) }
    }
  }
  return out
})

const landingTitle = computed(() => landing.value?.title || CONTENT.brand)
const landingPath = `/l/${slug}`

useHead(() => ({
  title: `${CONTENT.products.title} — ${landingTitle.value} | ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: CONTENT.products.description },
    { name: 'robots', content: 'noindex' }, // landing products page is not a canonical catalogue
  ],
}))
</script>

<template>
  <main class="pt-16 sm:pt-28">
    <!-- Back bar: home icon → returns to the landing page -->
    <div class="border-b border-line bg-surface-raised">
      <div class="mx-auto flex max-w-content items-center gap-3 px-5 py-3 sm:px-10">
        <NuxtLink
          :to="landingPath"
          class="flex items-center gap-2 text-sm text-ink-muted transition hover:text-gold-text"
          :aria-label="`بازگشت به ${landingTitle}`"
        >
          <House :size="16" aria-hidden="true" />
          <span>{{ landingTitle }}</span>
        </NuxtLink>
        <span class="text-line" aria-hidden="true">/</span>
        <span class="text-sm text-ink">{{ CONTENT.products.title }}</span>
      </div>
    </div>

    <div class="mx-auto max-w-content px-5 pb-16 sm:px-10">
      <header class="mb-6 mt-8">
        <p class="mb-1 text-xs tracking-[0.2em] text-gold-text">{{ CONTENT.products.eyebrow }}</p>
        <h1 class="text-2xl font-medium text-ink sm:text-4xl">{{ CONTENT.products.title }}</h1>
      </header>

      <GoldPriceStrip />

      <p class="mb-6 mt-4 text-sm text-ink-muted">
        {{ CONTENT.shop.resultCount(products.length) }}
      </p>

      <div
        v-if="products.length"
        class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-3 xl:grid-cols-4"
      >
        <ProductCard
          v-for="(p, i) in products"
          :key="p.id"
          :product="p"
          :index="i"
          shop
          :from="`/l/${slug}`"
          :from-title="landingTitle"
        />
      </div>

      <div v-else class="py-16 text-center">
        <p class="text-ink-muted">{{ CONTENT.shop.empty }}</p>
        <NuxtLink
          :to="landingPath"
          class="mt-4 inline-block border border-navy px-4 py-2 text-sm text-ink transition hover:bg-navy hover:text-white"
        >
          {{ CONTENT.nav.home }}
        </NuxtLink>
      </div>
    </div>
  </main>
</template>
