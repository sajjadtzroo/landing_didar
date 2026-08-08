<script setup lang="ts">
import { CONTENT } from '~/constants/content'

// Visual category chooser for /shop — mirrors the product `category` enum
// (daily | lux_daily | luxury). Clicking a card sets the active category (toggle
// off if already selected). Two-way bound so it drives the page's filter.
const model = defineModel<string>({ default: '' }) // '' = all
const props = defineProps<{ counts?: Record<string, number> }>()

const CATS = [
  { key: 'daily', label: CONTENT.products.daily.title },
  { key: 'lux_daily', label: CONTENT.products.lux_daily.title },
  { key: 'luxury', label: CONTENT.products.luxury.title },
] as const

function pick(key: string) {
  model.value = model.value === key ? '' : key
}
</script>

<template>
  <section class="mb-10">
    <h2 class="mb-4 text-lg font-medium text-ink sm:text-xl">{{ CONTENT.shop.categoriesTitle }}</h2>
    <div class="grid grid-cols-3 gap-3 sm:gap-5">
      <button
        v-for="c in CATS"
        :key="c.key"
        type="button"
        class="group flex flex-col items-center gap-3 border p-4 text-center transition sm:p-6"
        :class="model === c.key
          ? 'border-navy bg-navy text-white'
          : 'border-line bg-surface-raised text-ink hover:border-navy'"
        :aria-pressed="model === c.key"
        @click="pick(c.key)"
      >
        <!-- Custom line-art icons, one per category (inherit currentColor) -->
        <svg
          viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.4"
          stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
          class="h-10 w-10 transition-colors sm:h-12 sm:w-12"
          :class="model === c.key ? 'text-gold' : 'text-gold-text'"
        >
          <!-- daily → a simple ring -->
          <template v-if="c.key === 'daily'">
            <circle cx="24" cy="29" r="12" />
            <path d="M24 17 l4 -6 h-8 z" />
          </template>
          <!-- lux_daily → a pendant necklace -->
          <template v-else-if="c.key === 'lux_daily'">
            <path d="M9 12 C9 27 39 27 39 12" />
            <path d="M24 27 l4 5 -4 6 -4 -6 z" />
          </template>
          <!-- luxury → a faceted diamond -->
          <template v-else>
            <path d="M14 12 h20 l6 8 -16 18 -16 -18 z" />
            <path d="M8 20 h32" />
            <path d="M20 12 l-6 8 10 18 M28 12 l6 8 -10 18" />
          </template>
        </svg>
        <span class="text-sm font-medium sm:text-base">{{ c.label }}</span>
        <span
          v-if="counts?.[c.key] != null"
          class="tnum text-xs"
          :class="model === c.key ? 'text-white/70' : 'text-ink-muted'"
        >{{ CONTENT.shop.resultCount(counts[c.key]) }}</span>
      </button>
    </div>
  </section>
</template>
