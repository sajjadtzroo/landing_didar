<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio } from '~/types'

// One curated collection page at /shop/<slug>. Mirrors the landing detail page:
// slug-keyed fetch, 404 on miss, header (cover + name + breadcrumb), then the
// collection's product groups in the shop grid.
const route = useRoute()
const slug = route.params.slug as string
const base = useApiBase()

// Stable per-slug key (base URL differs server vs client — see l/[slug].vue note).
const { data: portfolio, error } = await useFetch<Portfolio>(`/portfolios/${slug}`, {
  baseURL: base,
  key: `portfolio-${slug}`,
})
if (error.value || !portfolio.value) {
  throw createError({ statusCode: 404, statusMessage: 'Portfolio not found', fatal: true })
}

// Drop empty groups (all product_ids resolved away as inactive/missing).
const groups = computed(() =>
  (portfolio.value?.groups || []).filter((g) => g.products.length),
)

const canonical = `${useSiteUrl()}/shop/${slug}`

useHead(() => ({
  title: `${portfolio.value?.name || CONTENT.shop.title} | ${CONTENT.brand}`,
  meta: [
    { property: 'og:title', content: portfolio.value?.name || CONTENT.shop.title },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: canonical },
    ...(portfolio.value?.cover_image_url
      ? [{ property: 'og:image', content: portfolio.value.cover_image_url }]
      : []),
  ],
  link: [{ rel: 'canonical', href: canonical }],
}))
</script>

<template>
  <main class="pt-16 sm:pt-28">
    <div class="mx-auto max-w-content px-5 sm:px-10">
      <!-- Breadcrumb -->
      <nav class="mb-6 flex items-center gap-2 text-sm text-ink-muted" aria-label="مسیر">
        <NuxtLink to="/" class="hover:text-gold-text">{{ CONTENT.nav.home }}</NuxtLink>
        <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
        <NuxtLink to="/shop" class="hover:text-gold-text">{{ CONTENT.nav.shop }}</NuxtLink>
        <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
        <span class="text-ink">{{ portfolio!.name }}</span>
      </nav>

      <!-- Header: cover banner with name overlaid, or plain heading -->
      <div
        v-if="portfolio!.cover_image_url"
        class="relative mb-8 aspect-[16/6] w-full overflow-hidden border border-line"
      >
        <NuxtImg
          :src="portfolio!.cover_image_url"
          :alt="portfolio!.name"
          class="h-full w-full object-cover"
          loading="eager"
          sizes="100vw"
        />
        <div class="absolute inset-0 flex items-end bg-gradient-to-t from-black/55 to-transparent p-5">
          <h1 class="text-2xl font-medium text-white sm:text-4xl">{{ portfolio!.name }}</h1>
        </div>
      </div>
      <h1 v-else class="mb-8 text-2xl font-medium text-ink sm:text-4xl">{{ portfolio!.name }}</h1>
    </div>

    <!-- Product groups -->
    <ProductGrid
      v-for="(g, i) in groups"
      :key="i"
      :flush="i > 0"
      :products="g.products"
      :eyebrow="g.eyebrow ?? undefined"
      :title="g.title"
      :description="g.description ?? undefined"
    />
  </main>
</template>
