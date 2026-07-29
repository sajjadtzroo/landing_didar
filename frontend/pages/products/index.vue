<script setup lang="ts">
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'

// Full catalogue grid. Reuses the same 'products' payload key as the landing.
const { data: products } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})

useHead({
  title: `${CONTENT.products.title} | ${CONTENT.brand}`,
  meta: [{ name: 'description', content: CONTENT.products.description }],
})
</script>

<template>
  <main class="pt-20">
    <ProductGrid :products="products || []" />
  </main>
</template>
