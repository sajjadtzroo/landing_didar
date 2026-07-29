<script setup lang="ts">
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

interface Stats {
  orders_today: number
  orders_week: number
  orders_month: number
  top_products: { name: string; quantity: number }[]
  by_province: { province: string; count: number }[]
  conversion_rate: number
}

const { data: stats } = await useAsyncData('admin-stats', () =>
  apiFetch<Stats>('/admin/stats'),
)

const cards = computed(() => [
  { label: 'سفارش امروز', value: stats.value?.orders_today ?? 0 },
  { label: 'این هفته', value: stats.value?.orders_week ?? 0 },
  { label: 'این ماه', value: stats.value?.orders_month ?? 0 },
  {
    label: 'نرخ تبدیل',
    value: `${toFa(Math.round((stats.value?.conversion_rate ?? 0) * 100))}٪`,
  },
])
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-medium">داشبورد</h1>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div v-for="c in cards" :key="c.label" class="border border-line bg-surface-raised p-5">
        <p class="text-sm text-ink-muted">{{ c.label }}</p>
        <p class="tnum mt-2 text-3xl font-medium text-gold-text">
          {{ typeof c.value === 'number' ? toFa(c.value) : c.value }}
        </p>
      </div>
    </div>

    <div class="mt-8 grid gap-6 md:grid-cols-2">
      <div class="border border-line bg-surface-raised p-5">
        <h2 class="mb-4 text-lg font-medium">پرفروش‌ترین محصولات</h2>
        <ul class="space-y-2 text-sm">
          <li
            v-for="p in stats?.top_products"
            :key="p.name"
            class="flex justify-between border-b border-line pb-2"
          >
            <span>{{ p.name }}</span>
            <span class="tnum text-gold-text">{{ toFa(p.quantity) }}</span>
          </li>
          <li v-if="!stats?.top_products?.length" class="text-ink-muted">داده‌ای نیست.</li>
        </ul>
      </div>

      <div class="border border-line bg-surface-raised p-5">
        <h2 class="mb-4 text-lg font-medium">سفارش‌ها بر اساس استان</h2>
        <ul class="space-y-2 text-sm">
          <li
            v-for="p in stats?.by_province"
            :key="p.province"
            class="flex justify-between border-b border-line pb-2"
          >
            <span>{{ p.province }}</span>
            <span class="tnum text-gold-text">{{ toFa(p.count) }}</span>
          </li>
          <li v-if="!stats?.by_province?.length" class="text-ink-muted">داده‌ای نیست.</li>
        </ul>
      </div>
    </div>
  </div>
</template>
