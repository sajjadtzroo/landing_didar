<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { AuditListResponse } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const filters = reactive({ actor: '', page: 1 })

const { data, refresh } = await useAsyncData(
  'admin-audit',
  () => {
    const p = new URLSearchParams({ page: String(filters.page) })
    if (filters.actor.trim()) p.set('actor', filters.actor.trim())
    return apiFetch<AuditListResponse>(`/admin/audit?${p}`)
  },
  { watch: [() => filters.page] },
)
const debounced = useDebounceFn(() => {
  filters.page = 1
  refresh()
}, 300)
watch(() => filters.actor, debounced)

function faDateTime(iso: string) {
  return toFa(new Date(iso).toLocaleString('en-GB'))
}
function statusClass(s: number | null) {
  if (s == null) return 'text-ink-muted'
  return s < 400 ? 'text-success' : 'text-danger'
}
</script>

<template>
  <div>
    <AdminPageHeader title="گزارش فعالیت" subtitle="هر تغییر در پنل مدیریت با نام کاربر ثبت می‌شود." />

    <input
      v-model="filters.actor"
      type="search"
      placeholder="فیلتر بر اساس نام کاربری"
      dir="ltr"
      class="form-control mb-4 h-11 sm:max-w-xs"
      aria-label="فیلتر کاربر"
    />

    <p v-if="data" class="tnum mb-3 text-xs text-ink-muted">{{ toFa(data.total) }} رویداد</p>

    <div class="admin-card overflow-x-auto p-0">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">زمان</th>
            <th class="p-3 text-start">کاربر</th>
            <th class="p-3 text-start">عملیات</th>
            <th class="p-3 text-start">نتیجه</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in data?.items" :key="a.id" class="border-t border-line">
            <td class="tnum whitespace-nowrap p-3 text-ink-muted">{{ faDateTime(a.created_at) }}</td>
            <td class="tnum p-3 font-medium" dir="ltr">{{ a.actor }}</td>
            <td class="tnum p-3" dir="ltr">{{ a.action }}</td>
            <td class="tnum p-3" :class="statusClass(a.status)">{{ a.status ?? '—' }}</td>
          </tr>
          <tr v-if="!data?.items?.length">
            <td colspan="4" class="p-10 text-center text-ink-muted">رویدادی ثبت نشده است.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="data && data.total > data.page_size" class="mt-6 flex items-center justify-center gap-4">
      <button class="h-10 border border-line px-4 text-sm disabled:opacity-50" :disabled="filters.page <= 1" @click="filters.page--">قبلی</button>
      <span class="tnum text-sm text-ink-muted">صفحه {{ toFa(filters.page) }}</span>
      <button class="h-10 border border-line px-4 text-sm disabled:opacity-50" :disabled="filters.page * data.page_size >= data.total" @click="filters.page++">بعدی</button>
    </div>
  </div>
</template>
