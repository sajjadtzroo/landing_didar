<script setup lang="ts">
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

// One set of filter controls shared by the desktop sidebar and the mobile
// sheet — the layout containers differ, the logic must not (spec: no
// duplicated filter logic). All state is v-model'd through to useShopFilters.
export interface CollectionOption {
  slug: string
  name: string
  count: number
}

defineProps<{
  collections: CollectionOption[]
  karats: number[]
  karatCounts: Record<number, number>
}>()

const collection = defineModel<string>('collection', { default: '' })
const weightMin = defineModel<string>('weightMin', { default: '' })
const weightMax = defineModel<string>('weightMax', { default: '' })
const ojratMin = defineModel<string>('ojratMin', { default: '' })
const ojratMax = defineModel<string>('ojratMax', { default: '' })
const karat = defineModel<number | ''>('karat', { default: '' })
</script>

<template>
  <div class="space-y-6">
    <!-- Collection (portfolio) — single-select; zero-count options disabled -->
    <div v-if="collections.length" class="flex flex-col gap-1.5">
      <span class="text-sm text-ink-muted">{{ CONTENT.nav.collections }}</span>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="h-11 border px-4 text-sm transition"
          :class="collection === '' ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
          :aria-pressed="collection === ''"
          @click="collection = ''"
        >
          {{ CONTENT.shop.all }}
        </button>
        <button
          v-for="c in collections"
          :key="c.slug"
          type="button"
          class="h-11 border px-4 text-sm transition disabled:cursor-not-allowed disabled:opacity-40"
          :class="collection === c.slug ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
          :disabled="c.count === 0"
          :aria-pressed="collection === c.slug"
          @click="collection = collection === c.slug ? '' : c.slug"
        >
          {{ c.name }}
          <span class="tnum ms-1 text-xs opacity-70">({{ toFa(c.count) }})</span>
        </button>
      </div>
    </div>

    <!-- Weight range -->
    <div class="flex flex-col gap-1.5">
      <span class="text-sm text-ink-muted">{{ CONTENT.shop.weightLabel }}</span>
      <div class="flex items-center gap-2">
        <input v-model="weightMin" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.minLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.weightLabel} ${CONTENT.shop.minLabel}`" />
        <span class="text-ink-muted">–</span>
        <input v-model="weightMax" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.maxLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.weightLabel} ${CONTENT.shop.maxLabel}`" />
      </div>
    </div>

    <!-- اجرت range -->
    <div class="flex flex-col gap-1.5">
      <span class="text-sm text-ink-muted">{{ CONTENT.shop.ojratLabel }}</span>
      <div class="flex items-center gap-2">
        <input v-model="ojratMin" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.minLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.ojratLabel} ${CONTENT.shop.minLabel}`" />
        <span class="text-ink-muted">–</span>
        <input v-model="ojratMax" type="number" min="0" inputmode="decimal" :placeholder="CONTENT.shop.maxLabel" class="form-control h-11" :aria-label="`${CONTENT.shop.ojratLabel} ${CONTENT.shop.maxLabel}`" />
      </div>
    </div>

    <!-- عیار chips (only when the catalog actually varies) -->
    <div v-if="karats.length > 1" class="flex flex-col gap-1.5">
      <span class="text-sm text-ink-muted">{{ CONTENT.shop.karatLabel }}</span>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="h-11 border px-4 text-sm transition"
          :class="karat === '' ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
          :aria-pressed="karat === ''"
          @click="karat = ''"
        >
          {{ CONTENT.shop.all }}
        </button>
        <button
          v-for="k in karats"
          :key="k"
          type="button"
          class="tnum h-11 border px-4 text-sm transition"
          :class="karat === k ? 'border-navy bg-navy text-white' : 'border-line text-ink-muted hover:border-navy'"
          :aria-pressed="karat === k"
          @click="karat = karat === k ? '' : k"
        >
          {{ toFa(k) }}
          <span class="ms-1 text-xs opacity-70">({{ toFa(karatCounts[k] ?? 0) }})</span>
        </button>
      </div>
    </div>
  </div>
</template>
