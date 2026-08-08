<script setup lang="ts">
import { Download, Search } from 'lucide-vue-next'
import { reactive, watch } from 'vue'
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
  page: 1,
})

function query() {
  const p = new URLSearchParams()
  if (filters.q) p.set('q', filters.q)
  if (filters.status) p.set('status', filters.status)
  if (filters.province) p.set('province', filters.province)
  p.set('page', String(filters.page))
  return p.toString()
}

const { data, refresh } = await useAsyncData(
  'admin-orders',
  () => apiFetch<OrderListResponse>(`/admin/orders?${query()}`),
  { watch: [() => filters.page] },
)

// Debounced re-fetch on filter change; reset to page 1.
const debounced = useDebounceFn(() => {
  filters.page = 1
  refresh()
}, 300)
watch(() => [filters.q, filters.status, filters.province], debounced)

watch(
  () => data.value?.unread,
  (n) => n != null && auth.setUnread(n),
  { immediate: true },
)

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
    <div class="mb-4 grid gap-3 sm:grid-cols-3">
      <div class="relative">
        <Search :size="16" class="absolute inset-y-0 end-3 my-auto text-ink-muted" />
        <input
          v-model="filters.q"
          type="search"
          placeholder="نام، موبایل یا فروشگاه"
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
    </div>

    <!-- Desktop table -->
    <div class="hidden overflow-x-auto border border-line md:block">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">تاریخ</th>
            <th class="p-3 text-start">نام</th>
            <th class="p-3 text-start">موبایل</th>
            <th class="p-3 text-start">فروشگاه</th>
            <th class="p-3 text-start">استان</th>
            <th class="p-3 text-start">وزن</th>
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
            <td class="tnum p-3">{{ faDate(o.created_at) }}</td>
            <td class="p-3">
              <span v-if="!o.is_read" class="me-1 inline-block h-2 w-2 rounded-full bg-gold" />
              {{ o.full_name }}
            </td>
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
        class="block w-full border border-line bg-surface-raised p-4 text-start"
        @click="navigateTo(`/admin/orders/${o.id}`)"
      >
        <div class="flex items-center justify-between">
          <span :class="!o.is_read ? 'font-medium' : ''">
            <span v-if="!o.is_read" class="me-1 inline-block h-2 w-2 rounded-full bg-gold" />
            {{ o.full_name }}
          </span>
          <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[o.status]">
            {{ STATUS_LABEL[o.status] }}
          </span>
        </div>
        <p class="tnum mt-1 text-sm text-ink-muted" dir="ltr">{{ o.phone }}</p>
        <p class="mt-1 text-sm text-ink-muted">{{ o.store_name }} — {{ o.province }}</p>
        <p class="tnum mt-1 text-sm text-gold-text">{{ formatGrams(o.total) ?? '—' }}</p>
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
