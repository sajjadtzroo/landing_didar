<script setup lang="ts">
import { computed } from 'vue'
import { Bar, Doughnut, Line } from 'vue-chartjs'
import { STATUS_LABEL } from '~/constants/orderStatus'
import type { AdminOrder, OrderListResponse, OrderStatus } from '~/types'
import {
  BRAND,
  STATUS_COLORS,
  baseOptions,
  categoryScales,
  registerCharts,
} from '~/utils/chart'
import { formatPrice, toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })
registerCharts()

interface Stats {
  orders_today: number
  orders_week: number
  orders_month: number
  total_orders: number
  total_value: number
  unread: number
  conversion_rate: number
  orders_by_day: { date: string; count: number }[]
  by_status: { status: OrderStatus; count: number }[]
  top_products: { name: string; quantity: number }[]
  by_province: { province: string; count: number }[]
}

const { data: stats } = await useAsyncData('admin-stats', () =>
  apiFetch<Stats>('/admin/stats'),
)
const { data: recent } = await useAsyncData('admin-recent-orders', () =>
  apiFetch<OrderListResponse>('/admin/orders?page=1&page_size=6'),
)

const cards = computed(() => [
  { label: 'سفارش امروز', value: toFa(stats.value?.orders_today ?? 0) },
  { label: 'این هفته', value: toFa(stats.value?.orders_week ?? 0) },
  { label: 'این ماه', value: toFa(stats.value?.orders_month ?? 0) },
  { label: 'کل سفارش‌ها', value: toFa(stats.value?.total_orders ?? 0) },
  { label: 'ارزش کل', value: formatPrice(stats.value?.total_value ?? 0) ?? '—' },
  { label: 'خوانده‌نشده', value: toFa(stats.value?.unread ?? 0) },
  {
    label: 'نرخ تبدیل',
    value: `${toFa(Math.round((stats.value?.conversion_rate ?? 0) * 100))}٪`,
  },
])

// --- Chart data ---
function faDay(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit' }))
}

const trendData = computed(() => ({
  labels: (stats.value?.orders_by_day ?? []).map((d) => faDay(d.date)),
  datasets: [
    {
      data: (stats.value?.orders_by_day ?? []).map((d) => d.count),
      borderColor: BRAND.gold,
      backgroundColor: 'rgba(176,138,87,0.14)',
      fill: true,
      tension: 0.35,
      pointRadius: 2,
      pointBackgroundColor: BRAND.gold,
    },
  ],
}))

const statusData = computed(() => {
  const rows = (stats.value?.by_status ?? []).filter((s) => s.count > 0)
  return {
    labels: rows.map((s) => STATUS_LABEL[s.status]),
    datasets: [
      {
        data: rows.map((s) => s.count),
        backgroundColor: rows.map((s) => STATUS_COLORS[s.status]),
        borderWidth: 0,
      },
    ],
  }
})
const hasStatus = computed(() => statusData.value.labels.length > 0)

const provinceData = computed(() => ({
  labels: (stats.value?.by_province ?? []).slice(0, 8).map((p) => p.province),
  datasets: [
    {
      data: (stats.value?.by_province ?? []).slice(0, 8).map((p) => p.count),
      backgroundColor: BRAND.navy,
      borderRadius: 2,
    },
  ],
}))
const hasProvince = computed(() => provinceData.value.labels.length > 0)

const productData = computed(() => ({
  labels: (stats.value?.top_products ?? []).map((p) => p.name),
  datasets: [
    {
      data: (stats.value?.top_products ?? []).map((p) => p.quantity),
      backgroundColor: BRAND.goldSoft,
      borderRadius: 2,
    },
  ],
}))
const hasProducts = computed(() => productData.value.labels.length > 0)

const barOpts = baseOptions({ scales: categoryScales(true), indexAxis: 'y' as const })
const lineOpts = baseOptions({ scales: categoryScales(false) })
const donutOpts = baseOptions({
  cutout: '62%',
  plugins: { legend: { display: true, position: 'bottom' as const, labels: { font: { family: 'Doran' } } } },
})

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-medium">داشبورد</h1>

    <!-- KPI cards -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
      <div
        v-for="c in cards"
        :key="c.label"
        class="border border-line bg-surface-raised p-4"
      >
        <p class="text-xs text-ink-muted">{{ c.label }}</p>
        <p class="tnum mt-2 text-xl font-medium text-gold-text">{{ c.value }}</p>
      </div>
    </div>

    <!-- Orders trend -->
    <div class="mt-8 border border-line bg-surface-raised p-5">
      <h2 class="mb-4 text-lg font-medium">روند سفارش‌ها (۱۴ روز)</h2>
      <div class="h-64">
        <ClientOnly><Line :data="trendData" :options="lineOpts" /></ClientOnly>
      </div>
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-2">
      <!-- Status donut -->
      <div class="border border-line bg-surface-raised p-5">
        <h2 class="mb-4 text-lg font-medium">وضعیت سفارش‌ها</h2>
        <div class="h-64">
          <ClientOnly>
            <Doughnut v-if="hasStatus" :data="statusData" :options="donutOpts" />
            <p v-else class="pt-20 text-center text-ink-muted">داده‌ای نیست.</p>
          </ClientOnly>
        </div>
      </div>

      <!-- Province bar -->
      <div class="border border-line bg-surface-raised p-5">
        <h2 class="mb-4 text-lg font-medium">سفارش‌ها بر اساس استان</h2>
        <div class="h-64">
          <ClientOnly>
            <Bar v-if="hasProvince" :data="provinceData" :options="barOpts" />
            <p v-else class="pt-20 text-center text-ink-muted">داده‌ای نیست.</p>
          </ClientOnly>
        </div>
      </div>
    </div>

    <!-- Top products -->
    <div class="mt-6 border border-line bg-surface-raised p-5">
      <h2 class="mb-4 text-lg font-medium">پرفروش‌ترین محصولات</h2>
      <div class="h-64">
        <ClientOnly>
          <Bar v-if="hasProducts" :data="productData" :options="barOpts" />
          <p v-else class="pt-20 text-center text-ink-muted">داده‌ای نیست.</p>
        </ClientOnly>
      </div>
    </div>

    <!-- Recent orders -->
    <div class="mt-6 border border-line bg-surface-raised p-5">
      <h2 class="mb-4 text-lg font-medium">آخرین سفارش‌ها</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-start text-sm">
          <thead class="text-ink-muted">
            <tr>
              <th class="p-2 text-start">تاریخ</th>
              <th class="p-2 text-start">نام</th>
              <th class="p-2 text-start">فروشگاه</th>
              <th class="p-2 text-start">مبلغ</th>
              <th class="p-2 text-start">وضعیت</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="o in (recent?.items as AdminOrder[] | undefined)"
              :key="o.id"
              class="cursor-pointer border-t border-line hover:bg-surface-soft"
              @click="navigateTo(`/admin/orders/${o.id}`)"
            >
              <td class="tnum p-2">{{ faDate(o.created_at) }}</td>
              <td class="p-2">{{ o.full_name }}</td>
              <td class="p-2">{{ o.store_name }}</td>
              <td class="tnum p-2">{{ formatPrice(o.total) ?? '—' }}</td>
              <td class="p-2">{{ STATUS_LABEL[o.status] }}</td>
            </tr>
            <tr v-if="!recent?.items?.length">
              <td colspan="5" class="p-6 text-center text-ink-muted">سفارشی نیست.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
