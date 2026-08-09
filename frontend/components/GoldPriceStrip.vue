<script setup lang="ts">
// نرخ روز strip: the live 18k per-gram rate from the public /prices board (TGJU).
// The anchor figure of every Iranian gold storefront — informational market data,
// so it doesn't conflict with the price-on-request ordering model.
import { TrendingDown, TrendingUp } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

interface PriceItem {
  symbol: string
  price: number
  change_pct: number
  direction: 'high' | 'low' | 'none'
  updated_at: string | null
}

const { data, refresh } = await useFetch<{ items: PriceItem[] }>('/prices', {
  baseURL: useApiBase(),
  key: 'public-prices',
  default: () => ({ items: [] }),
})

// Backend refreshes every 2 min; poll on the same cadence while visible.
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => { timer = setInterval(refresh, 120_000) })
onBeforeUnmount(() => clearInterval(timer))

const gram18 = computed(() =>
  (data.value?.items ?? []).find((i) => i.symbol === 'geram18'),
)
</script>

<template>
  <!-- Renders nothing when the rate is unavailable — no empty chrome. -->
  <div
    v-if="gram18"
    class="corner-soft mb-8 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 border
      border-gold/30 bg-surface-raised px-4 py-3 text-sm sm:justify-between sm:px-6"
  >
    <span class="flex items-center gap-2 text-ink-muted">
      <span class="relative flex h-2 w-2" aria-hidden="true">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60 motion-reduce:hidden" />
        <span class="relative inline-flex h-2 w-2 rounded-full bg-success" />
      </span>
      {{ CONTENT.shop.goldPriceLabel }}
    </span>

    <span class="flex items-center gap-3">
      <span class="tnum text-lg font-medium text-ink">
        {{ toFa(Math.round(gram18.price).toLocaleString('en-US')) }}
        <span class="text-xs font-normal text-ink-muted">{{ CONTENT.shop.goldPriceUnit }}</span>
      </span>
      <span
        class="tnum corner-soft flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
        :class="gram18.direction === 'low' ? 'bg-danger-soft text-danger' : 'bg-success-soft text-success'"
      >
        <component
          :is="gram18.direction === 'low' ? TrendingDown : TrendingUp"
          :size="13"
          aria-hidden="true"
        />
        {{ toFa(Math.abs(gram18.change_pct)) }}٪
      </span>
      <span v-if="gram18.updated_at" class="tnum hidden text-xs text-ink-muted sm:inline">
        {{ CONTENT.shop.goldPriceUpdated(toFa(gram18.updated_at)) }}
      </span>
    </span>
  </div>
</template>
