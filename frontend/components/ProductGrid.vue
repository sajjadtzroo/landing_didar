<script setup lang="ts">
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'

defineProps<{ products: Product[] }>()

const { trackEvent } = useAnalytics()

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
  <section id="products" ref="section" class="bg-surface py-16">
    <div class="mx-auto max-w-content px-5 sm:px-10">
      <SectionDivider
        :eyebrow="CONTENT.products.eyebrow"
        :title="CONTENT.products.title"
        :description="CONTENT.products.description"
      />
      <div class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
        <ProductCard
          v-for="(product, i) in products"
          :key="product.id"
          :product="product"
          :index="i"
        />
      </div>
    </div>
  </section>
</template>
