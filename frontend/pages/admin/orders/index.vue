<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from 'lucide-vue-next'
import { computed, reactive, watch } from 'vue'
import { PROVINCES } from '~/constants/provinces'
import { STATUS_CLASS, STATUS_FLOW, STATUS_LABEL } from '~/constants/orderStatus'
import type { OrderListResponse, OrderStatus } from '~/types'
import { formatGrams, toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const auth = useAdminAuth()
const filters = reactive({
  q: '',
  status: '' as '' | OrderStatus,
  province: '',
  sort: 'created_at',
  dir: 'desc' as 'asc' | 'desc',
  page: 1,
})

function query() {
  const p = new URLSearchParams()
  if (filters.q) p.set('q', filters.q)
  if (filters.status) p.set('status', filters.status)
  if (filters.province) p.set('province', filters.province)
  p.set('sort', filters.sort)
  p.set('dir', filters.dir)
  p.set('page', String(filters.page))
  return p.toString()
}

const { data, refresh } = await useAsyncData(
  'admin-orders',
  () => apiFetch<OrderListResponse>(`/admin/orders?${query()}`),
  { watch: [() => filters.page] },
)

// Debounced re-fetch on filter/sort change; reset to page 1.
const debounced = useDebounceFn(() => {
  filters.page = 1
  refresh()
}, 300)
watch(
  () => [filters.q, filters.status, filters.province, filters.sort, filters.dir],
  debounced,
)

watch(
  () => data.value?.unread,
  (n) => n != null && auth.setUnread(n),
  { immediate: true },
)

// Column sort: click a header to sort by it; click again to flip direction.
// Names default to A→Z; everything else newest / heaviest first.
function sortBy(col: string) {
  if (filters.sort === col) {
    filters.dir = filters.dir === 'asc' ? 'desc' : 'asc'
  } else {
    filters.sort = col
    filters.dir = col === 'full_name' ? 'asc' : 'desc'
  }
}
function sortIcon(col: string) {
  if (filters.sort !== col) return ArrowUpDown
  return filters.dir === 'asc' ? ArrowUp : ArrowDown
}

// Mobile sort control binds a single "col|dir" string.
const sortValue = computed({
  get: () => `${filters.sort}|${filters.dir}`,
  set: (v: string) => {
    const [c, d] = v.split('|')
    filters.sort = c
    filters.dir = d as 'asc' | 'desc'
  },
})
const SORT_OPTIONS = [
  { value: 'created_at|desc', label: 'جدیدترین' },
  { value: 'created_at|asc', label: 'قدیمی‌ترین' },
  { value: 'total|desc', label: 'سنگین‌ترین' },
  { value: 'total|asc', label: 'سبک‌ترین' },
  { value: 'full_name|asc', label: 'نام (الف تا ی)' },
]

function exportCsv() {
  const url = `${useApiBase()}/admin/orders/export?${query()}`
  window.open(url, '_blank')
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <AdminPageHeader title="سفارش‌ها">
      <button
        class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold"
        @click="exportCsv"
      >
        <Download :size="16" /> خروجی CSV
      </button>
    </AdminPageHeader>

    <!-- Filters -->
    <div class="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div class="relative sm:col-span-2 lg:col-span-1">
        <Search :size="16" class="absolute inset-y-0 end-3 my-auto text-ink-muted" />
        <input
          v-model="filters.q"
          type="search"
          placeholder="شماره سفارش، نام، موبایل یا فروشگاه"
          class="form-control pe-9"
        />
      </div>
      <select v-model="filters.status" class="form-control">
        <option value="">همه وضعیت‌ها</option>
        <option v-for="s in STATUS_FLOW" :key="s" :value="s">{{ STATUS_LABEL[s] }}</option>
      </select>
      <select v-model="filters.province" class="form-control">
        <option value="">همه استان‌ها</option>
        <option v-for="p in PROVINCES" :key="p.value" :value="p.value">{{ p.label }}</option>
      </select>
      <!-- Sort (works on every screen; desktop also has clickable headers) -->
      <select v-model="sortValue" class="form-control" aria-label="مرتب‌سازی">
        <option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">
          مرتب‌سازی: {{ o.label }}
        </option>
      </select>
    </div>

    <!-- Result count -->
    <p v-if="data" class="tnum mb-3 text-xs text-ink-muted">
      {{ toFa(data.total) }} سفارش
    </p>

    <!-- Desktop table -->
    <div class="hidden overflow-x-auto border border-line md:block">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">شماره سفارش</th>
            <th class="p-3 text-start">
              <button type="button" class="inline-flex items-center gap-1 hover:text-gold-text" @click="sortBy('created_at')">
                تاریخ
                <component :is="sortIcon('created_at')" :size="13" :class="filters.sort === 'created_at' ? 'text-gold-text' : 'opacity-40'" />
              </button>
            </th>
            <th class="p-3 text-start">
              <button type="button" class="inline-flex items-center gap-1 hover:text-gold-text" @click="sortBy('full_name')">
                نام
                <component :is="sortIcon('full_name')" :size="13" :class="filters.sort === 'full_name' ? 'text-gold-text' : 'opacity-40'" />
              </button>
            </th>
            <th class="p-3 text-start">موبایل</th>
            <th class="p-3 text-start">فروشگاه</th>
            <th class="p-3 text-start">استان</th>
            <th class="p-3 text-start">
              <button type="button" class="inline-flex items-center gap-1 hover:text-gold-text" @click="sortBy('total')">
                وزن
                <component :is="sortIcon('total')" :size="13" :class="filters.sort === 'total' ? 'text-gold-text' : 'opacity-40'" />
              </button>
            </th>
            <th class="p-3 text-start">وضعیت</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="o in data?.items"
            :key="o.id"
            class="cursor-pointer border-t border-line hover:bg-surface-soft"
            :class="!o.is_read ? 'font-medium' : ''"
            @click="navigateTo(`/admin/orders/${o.id}`)"
          >
            <td class="p-3">
              <span class="inline-flex items-center gap-2">
                <span v-if="!o.is_read" class="inline-block h-2 w-2 shrink-0 rounded-full bg-gold" aria-label="خوانده‌نشده" />
                <span class="tnum font-medium text-gold-text" dir="ltr">{{ o.reference }}</span>
              </span>
            </td>
            <td class="tnum p-3 text-ink-muted">{{ faDate(o.created_at) }}</td>
            <td class="p-3">{{ o.full_name }}</td>
            <td class="tnum p-3" dir="ltr">{{ o.phone }}</td>
            <td class="p-3">{{ o.store_name }}</td>
            <td class="p-3">{{ o.province }}</td>
            <td class="tnum p-3">{{ formatGrams(o.total) ?? '—' }}</td>
            <td class="p-3">
              <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[o.status]">
                {{ STATUS_LABEL[o.status] }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile cards -->
    <div class="space-y-3 md:hidden">
      <button
        v-for="o in data?.items"
        :key="o.id"
        class="admin-card admin-card--hover block w-full p-4 text-start"
        @click="navigateTo(`/admin/orders/${o.id}`)"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="inline-flex items-center gap-2">
            <span v-if="!o.is_read" class="inline-block h-2 w-2 shrink-0 rounded-full bg-gold" />
            <span class="tnum font-medium text-gold-text" dir="ltr">{{ o.reference }}</span>
          </span>
          <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[o.status]">
            {{ STATUS_LABEL[o.status] }}
          </span>
        </div>
        <p class="mt-2 text-sm" :class="!o.is_read ? 'font-medium' : ''">{{ o.full_name }}</p>
        <p class="tnum mt-1 text-sm text-ink-muted" dir="ltr">{{ o.phone }}</p>
        <div class="mt-1 flex items-center justify-between gap-2 text-sm text-ink-muted">
          <span>{{ o.store_name }} — {{ o.province }}</span>
          <span class="tnum text-gold-text">{{ formatGrams(o.total) ?? '—' }}</span>
        </div>
      </button>
    </div>

    <p v-if="!data?.items?.length" class="py-12 text-center text-ink-muted">سفارشی یافت نشد.</p>

    <!-- Pagination -->
    <div v-if="data && data.total > data.page_size" class="mt-6 flex items-center justify-center gap-4">
      <button
        class="h-10 border border-line px-4 text-sm disabled:opacity-50"
        :disabled="filters.page <= 1"
        @click="filters.page--"
      >
        قبلی
      </button>
      <span class="tnum text-sm text-ink-muted">صفحه {{ toFa(filters.page) }}</span>
      <button
        class="h-10 border border-line px-4 text-sm disabled:opacity-50"
        :disabled="filters.page * data.page_size >= data.total"
        @click="filters.page++"
      >
        بعدی
      </button>
    </div>
  </div>
</template>
