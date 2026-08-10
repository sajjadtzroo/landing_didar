<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

// Visual category chooser for /shop — the single source of truth for the active
// category (the filter bar no longer duplicates it). Mirrors the product
// `category` enum plus an "all" tile. Two-way bound; '' = all.
const model = defineModel<string>({ default: '' })
const props = defineProps<{ counts?: Record<string, number> }>()

const total = computed(() =>
  Object.values(props.counts ?? {}).reduce((n, v) => n + (v || 0), 0),
)

// key '' is the "all" tile; the rest map to the category enum.
const CATS = [
  { key: '', label: CONTENT.shop.allProducts },
  { key: 'daily', label: CONTENT.products.daily.title },
  { key: 'lux_daily', label: CONTENT.products.lux_daily.title },
  { key: 'luxury', label: CONTENT.products.luxury.title },
] as const

function count(key: string) {
  return key === '' ? total.value : (props.counts?.[key] ?? 0)
}
function pick(key: string) {
  // Tapping "all" clears; tapping a category selects it (no toggle-off — "all"
  // is the explicit reset now).
  model.value = key
}
</script>

<template>
  <section class="mb-10">
    <h2 class="mb-4 text-lg font-medium text-ink sm:text-xl">{{ CONTENT.shop.categoriesTitle }}</h2>
    <!-- Mobile: one horizontal snap row (the 2×2 tile grid ate ~40vh and pushed
         the catalogue below the fold); desktop keeps the four big tiles. -->
    <div
      class="-mx-5 flex snap-x snap-mandatory gap-3 overflow-x-auto px-5 pb-2
        sm:mx-0 sm:grid sm:grid-cols-4 sm:gap-5 sm:overflow-visible sm:px-0 sm:pb-0"
    >
      <button
        v-for="c in CATS"
        :key="c.key || 'all'"
        type="button"
        class="group relative flex w-[124px] shrink-0 snap-start flex-col items-center gap-2
          overflow-hidden border p-3 text-center transition duration-300 hover:-translate-y-1
          sm:w-auto sm:shrink sm:gap-3 sm:p-6"
        :class="model === c.key
          ? 'border-navy bg-navy text-white shadow-luxury'
          : 'border-line bg-surface-raised text-ink hover:border-navy'"
        :aria-pressed="model === c.key"
        @click="pick(c.key)"
      >
        <!-- Icon in a gold ring -->
        <span
          class="flex h-11 w-11 items-center justify-center rounded-full border transition-colors sm:h-16 sm:w-16"
          :class="model === c.key ? 'border-white/25 bg-white/10' : 'border-line group-hover:border-gold'"
          aria-hidden="true"
        >
          <svg
            viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.4"
            stroke-linecap="round" stroke-linejoin="round"
            class="h-6 w-6 transition-colors sm:h-9 sm:w-9"
            :class="model === c.key ? 'text-gold' : 'text-gold-text'"
          >
            <!-- all → four facets -->
            <template v-if="c.key === ''">
              <rect x="10" y="10" width="12" height="12" />
              <rect x="26" y="10" width="12" height="12" />
              <rect x="10" y="26" width="12" height="12" />
              <rect x="26" y="26" width="12" height="12" />
            </template>
            <!-- daily → a simple ring -->
            <template v-else-if="c.key === 'daily'">
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
        </span>

        <span class="whitespace-nowrap text-xs font-medium sm:whitespace-normal sm:text-base">{{ c.label }}</span>

        <!-- Count as a pill -->
        <span
          class="tnum corner-soft px-2 py-0.5 text-xs"
          :class="model === c.key ? 'bg-white/10 text-white/80' : 'bg-surface-soft text-gold-text'"
        >{{ CONTENT.shop.resultCount(count(c.key)) }}</span>

        <!-- Signature gold accent: grows from the start edge on hover -->
        <span
          v-if="model !== c.key"
          class="pointer-events-none absolute inset-x-0 bottom-0 h-1 origin-right scale-x-0
            bg-gold transition-transform duration-500 group-hover:scale-x-100"
        />
      </button>
    </div>
  </section>
</template>
