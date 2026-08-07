<script setup lang="ts">
import { computed } from 'vue'
import type { Portfolio } from '~/types'

// One admin-curated collection rendered atop /shop: optional cover banner + name,
// then each group's products in the shop grid (price + add-to-cart cards).
const props = defineProps<{ portfolio: Portfolio }>()

// Drop empty groups (all product_ids resolved away as inactive/missing).
const groups = computed(() =>
  props.portfolio.groups.filter((g) => g.products.length),
)
</script>

<template>
  <section v-if="groups.length" class="mb-10">
    <!-- Cover banner (name overlaid) or plain name heading -->
    <div
      v-if="portfolio.cover_image_url"
      class="relative mb-6 aspect-[16/6] w-full overflow-hidden border border-line"
    >
      <NuxtImg
        :src="portfolio.cover_image_url"
        :alt="portfolio.name"
        class="h-full w-full object-cover"
        loading="lazy"
      />
      <div class="absolute inset-0 flex items-end bg-gradient-to-t from-black/55 to-transparent p-5">
        <h2 class="text-2xl font-medium text-white sm:text-3xl">{{ portfolio.name }}</h2>
      </div>
    </div>
    <h2 v-else class="mb-6 text-2xl font-medium text-ink sm:text-3xl">{{ portfolio.name }}</h2>

    <div v-for="(g, gi) in groups" :key="gi" class="mb-8 last:mb-0">
      <div v-if="g.title || g.eyebrow || g.description" class="mb-4">
        <p v-if="g.eyebrow" class="mb-1 text-xs tracking-[0.2em] text-gold-text">{{ g.eyebrow }}</p>
        <h3 v-if="g.title" class="text-lg font-medium text-ink">{{ g.title }}</h3>
        <p v-if="g.description" class="mt-1 text-sm leading-7 text-ink-muted">{{ g.description }}</p>
      </div>
      <div class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
        <ProductCard
          v-for="(p, i) in g.products"
          :key="p.id"
          :product="p"
          :index="i"
          shop
        />
      </div>
    </div>
  </section>
</template>
