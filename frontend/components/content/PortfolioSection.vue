<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio } from '~/types'

// One admin-curated collection rendered atop /shop: optional cover banner + name,
// then each group's products in the shop grid (price + add-to-cart cards). The
// cover/heading link to the collection's own page at /shop/<slug>.
const props = defineProps<{ portfolio: Portfolio }>()

// Drop empty groups (all product_ids resolved away as inactive/missing).
const groups = computed(() =>
  props.portfolio.groups.filter((g) => g.products.length),
)
const to = computed(() => `/shop/${props.portfolio.slug}`)
</script>

<template>
  <section v-if="groups.length" class="mb-10">
    <!-- Cover banner (name overlaid) or plain name heading — links to the page -->
    <NuxtLink
      v-if="portfolio.cover_image_url"
      :to="to"
      class="group relative mb-6 block aspect-[16/6] w-full overflow-hidden border border-line"
    >
      <NuxtImg
        :src="portfolio.cover_image_url"
        :alt="portfolio.name"
        class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
        loading="lazy"
      />
      <div class="absolute inset-0 flex items-end justify-between gap-4 bg-gradient-to-t from-black/55 to-transparent p-5">
        <h2 class="text-2xl font-medium text-white sm:text-3xl">{{ portfolio.name }}</h2>
        <span class="hidden shrink-0 items-center gap-1 text-sm text-white/90 sm:flex">
          {{ CONTENT.shop.viewCollection }}
          <ChevronLeft :size="16" class="rotate-180" aria-hidden="true" />
        </span>
      </div>
    </NuxtLink>
    <div v-else class="mb-6 flex items-center justify-between gap-4">
      <h2 class="text-2xl font-medium text-ink sm:text-3xl">{{ portfolio.name }}</h2>
      <NuxtLink :to="to" class="flex shrink-0 items-center gap-1 text-sm text-gold-text hover:underline">
        {{ CONTENT.shop.viewCollection }}
        <ChevronLeft :size="16" class="rotate-180" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- Content-derived key: groups are a filtered computed, so indices shift
         when a middle group empties — an index key would recycle DOM across
         different groups. -->
    <div
      v-for="g in groups"
      :key="`${g.title}:${g.products[0]?.id ?? ''}`"
      class="mb-8 last:mb-0"
    >
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
