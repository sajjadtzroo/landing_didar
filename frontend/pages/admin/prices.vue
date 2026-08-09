<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

interface PriceItem {
  symbol: string
  label: string
  unit: 'toman' | 'usd'
  price: number
  change_pct: number
  direction: 'high' | 'low' | 'none'
  updated_at: string | null
}
interface PricesResp {
  items: PriceItem[]
  source: string
  cached?: boolean
  stale?: boolean
  error?: boolean
}

const { data, refresh } = await useAsyncData('admin-prices', () =>
  apiFetch<PricesResp>('/admin/prices'),
)

// Live-ish: re-poll while the page is open (TGJU + backend cache do the throttling).
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => { timer = setInterval(refresh, 60_000) })
onBeforeUnmount(() => clearInterval(timer))

const items = computed<PriceItem[]>(() => data.value?.items ?? [])
const stale = computed(() => data.value?.stale === true)
const errored = computed(() => data.value?.error === true)

const byId = computed(() => Object.fromEntries(items.value.map((i) => [i.symbol, i])))
const cards = computed(() =>
  ['geram18', 'geram24', 'mesghal', 'price_dollar_rl']
    .map((s) => byId.value[s])
    .filter(Boolean) as PriceItem[],
)

function price(it: PriceItem) {
  const n =
    it.unit === 'usd'
      ? it.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : Math.round(it.price).toLocaleString('en-US')
  return toFa(n)
}
function unitLabel(it: PriceItem) {
  return it.unit === 'usd' ? 'دلار' : 'تومان'
}
function changeText(it: PriceItem) {
  const sign = it.direction === 'low' ? '−' : '+'
  return `${sign}${toFa(Math.abs(it.change_pct))}٪`
}
function changeClass(it: PriceItem) {
  if (it.direction === 'high') return 'bg-success-soft text-success'
  if (it.direction === 'low') return 'bg-danger-soft text-danger'
  return 'bg-surface-soft text-ink-muted'
}
</script>

<template>
  <div>
    <AdminPageHeader title="قیمت طلا" subtitle="نرخ لحظه‌ای بازار برای مرجع قیمت‌گذاری.">
      <a
        href="https://www.tgju.org/gold-chart"
        target="_blank"
        rel="noopener"
        class="text-sm text-gold-text underline underline-offset-4 hover:no-underline"
      >
        مشاهده در TGJU
      </a>
    </AdminPageHeader>

    <p
      v-if="errored"
      role="alert"
      class="mb-4 border border-danger bg-danger-soft p-3 text-sm text-danger"
    >
      دریافت قیمت‌ها از TGJU ناموفق بود. بعداً دوباره تلاش کنید.
    </p>
    <p v-else-if="stale" class="mb-4 text-xs text-warning">
      اتصال به TGJU برقرار نشد؛ آخرین نرخ ذخیره‌شده نمایش داده می‌شود.
    </p>

    <!-- Headline cards -->
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div v-for="c in cards" :key="c.symbol" class="admin-card admin-card--hover p-4">
        <p class="text-xs text-ink-muted">{{ c.label }}</p>
        <p class="tnum mt-2 text-xl font-medium text-ink">
          {{ price(c) }} <span class="text-sm font-normal text-ink-muted">{{ unitLabel(c) }}</span>
        </p>
        <p class="tnum mt-1 text-xs" :class="c.direction === 'low' ? 'text-danger' : 'text-success'">
          {{ changeText(c) }}
        </p>
      </div>
    </div>

    <!-- Full board -->
    <div class="admin-card mt-8">
      <div class="overflow-x-auto">
        <table class="w-full text-start text-sm">
          <thead class="text-ink-muted">
            <tr class="border-b border-line">
              <th class="p-3 text-start font-normal">شاخص</th>
              <th class="p-3 text-start font-normal">قیمت</th>
              <th class="p-3 text-start font-normal">تغییر</th>
              <th class="p-3 text-start font-normal">آخرین بروزرسانی</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="it in items" :key="it.symbol" class="border-t border-line">
              <td class="p-3 text-ink">{{ it.label }}</td>
              <td class="tnum p-3 text-ink">
                {{ price(it) }}
                <span class="text-xs text-ink-muted">{{ unitLabel(it) }}</span>
              </td>
              <td class="p-3">
                <span
                  class="tnum corner-soft inline-block px-2 py-1 text-xs font-medium"
                  :class="changeClass(it)"
                >
                  {{ changeText(it) }}
                </span>
              </td>
              <td class="tnum p-3 text-ink-muted">{{ it.updated_at ? toFa(it.updated_at) : '—' }}</td>
            </tr>
            <tr v-if="!items.length">
              <td colspan="4" class="p-6 text-center text-ink-muted">قیمتی در دسترس نیست.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
