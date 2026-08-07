<script setup lang="ts">
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'

// Full catalogue grid. Reuses the same 'products' payload key as the landing.
const { data: products } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})

const canonical = `${useSiteUrl()}/products`

useHead({
  title: `${CONTENT.products.title} | ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: CONTENT.products.description },
    { property: 'og:title', content: `${CONTENT.products.title} | ${CONTENT.brand}` },
    { property: 'og:description', content: CONTENT.products.description },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: canonical },
  ],
  link: [{ rel: 'canonical', href: canonical }],
})
</script>

<template>
  <main class="pt-16 sm:pt-20">
    <ProductGrid :products="products || []" />
  </main>
</template>
