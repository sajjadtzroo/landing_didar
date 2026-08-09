<script setup lang="ts">
import { Download } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { BuybackListResponse, BuybackRequest } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const STATUS_LABEL: Record<BuybackRequest['status'], string> = {
  under_review: 'در حال بررسی',
  accepted: 'پذیرفته‌شده',
  rejected: 'ردشده',
}
const STATUS_CLASS: Record<BuybackRequest['status'], string> = {
  under_review: 'bg-warning-soft text-warning',
  accepted: 'bg-success-soft text-success',
  rejected: 'bg-danger-soft text-danger',
}

const filters = reactive({ status: '', page: 1 })

const { data, refresh } = await useAsyncData(
  'admin-buybacks',
  () => {
    const p = new URLSearchParams({ page: String(filters.page) })
    if (filters.status) p.set('status', filters.status)
    return apiFetch<BuybackListResponse>(`/admin/buybacks?${p}`)
  },
  { watch: [() => filters.page, () => filters.status] },
)

// --- Inline processing sheet ---
const panelOpen = ref(false)
const edit = reactive({ id: '', code: '', product: '', status: 'under_review' as BuybackRequest['status'], price: '', note: '' })
const saving = ref(false)

function startEdit(b: BuybackRequest) {
  Object.assign(edit, {
    id: b.id,
    code: b.code,
    product: b.product_name,
    status: b.status,
    price: b.offered_price ?? '',
    note: b.admin_note ?? '',
  })
  panelOpen.value = true
}
async function save() {
  saving.value = true
  try {
    await apiFetch(`/admin/buybacks/${edit.id}`, {
      method: 'PATCH',
      body: {
        status: edit.status,
        offered_price: edit.price === '' ? null : Number(edit.price),
        admin_note: edit.note || null,
      },
    })
    panelOpen.value = false
    await refresh()
  } finally {
    saving.value = false
  }
}

function exportCsv() {
  const p = filters.status ? `?status=${filters.status}` : ''
  window.open(`${useApiBase()}/admin/buybacks/export${p}`, '_blank')
}
function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <AdminPageHeader title="درخواست‌های بازخرید" subtitle="درخواست‌های ثبت‌شده روی شناسنامه قطعه‌ها؛ بررسی و قیمت‌گذاری.">
      <button class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold" @click="exportCsv">
        <Download :size="16" /> خروجی CSV
      </button>
    </AdminPageHeader>

    <select v-model="filters.status" class="form-control mb-4 h-11 sm:max-w-xs" aria-label="فیلتر وضعیت">
      <option value="">همه وضعیت‌ها</option>
      <option value="under_review">در حال بررسی</option>
      <option value="accepted">پذیرفته‌شده</option>
      <option value="rejected">ردشده</option>
    </select>

    <p v-if="data" class="tnum mb-3 text-xs text-ink-muted">{{ toFa(data.total) }} درخواست</p>

    <div class="admin-card overflow-x-auto p-0">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">کد قطعه</th>
            <th class="p-3 text-start">محصول</th>
            <th class="p-3 text-start">درخواست‌دهنده</th>
            <th class="p-3 text-start">وضعیت</th>
            <th class="p-3 text-start">قیمت پیشنهادی</th>
            <th class="p-3 text-start">تاریخ</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="b in data?.items"
            :key="b.id"
            class="cursor-pointer border-t border-line hover:bg-surface-soft"
            @click="startEdit(b)"
          >
            <td class="tnum p-3 font-medium text-gold-text" dir="ltr">{{ b.code }}</td>
            <td class="p-3">{{ b.product_name }}</td>
            <td class="p-3">
              {{ b.requester_name }}
              <span class="tnum block text-xs text-ink-muted" dir="ltr">{{ b.requester_phone }}</span>
            </td>
            <td class="p-3">
              <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[b.status]">{{ STATUS_LABEL[b.status] }}</span>
            </td>
            <td class="tnum p-3">{{ b.offered_price ? formatPrice(b.offered_price) : '—' }}</td>
            <td class="tnum p-3 text-ink-muted">{{ faDate(b.created_at) }}</td>
          </tr>
          <tr v-if="!data?.items?.length">
            <td colspan="6" class="p-10 text-center text-ink-muted">درخواستی ثبت نشده است.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="data && data.total > data.page_size" class="mt-6 flex items-center justify-center gap-4">
      <button class="h-10 border border-line px-4 text-sm disabled:opacity-50" :disabled="filters.page <= 1" @click="filters.page--">قبلی</button>
      <span class="tnum text-sm text-ink-muted">صفحه {{ toFa(filters.page) }}</span>
      <button class="h-10 border border-line px-4 text-sm disabled:opacity-50" :disabled="filters.page * data.page_size >= data.total" @click="filters.page++">بعدی</button>
    </div>

    <!-- Processing sheet -->
    <BaseSheet v-model="panelOpen" :title="`بررسی — ${edit.code}`">
      <div class="space-y-4">
        <p class="text-sm text-ink-muted">{{ edit.product }}</p>
        <FormField label="وضعیت" v-slot="{ id }">
          <select :id="id" v-model="edit.status" class="form-control">
            <option value="under_review">در حال بررسی</option>
            <option value="accepted">پذیرفته‌شده</option>
            <option value="rejected">ردشده</option>
          </select>
        </FormField>
        <FormField label="قیمت پیشنهادی (تومان)" v-slot="{ id }">
          <input :id="id" v-model="edit.price" type="number" min="0" dir="ltr" class="form-control" />
        </FormField>
        <FormField label="یادداشت داخلی" v-slot="{ id }">
          <input :id="id" v-model="edit.note" maxlength="300" class="form-control" />
        </FormField>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'در حال ذخیره…' : 'ذخیره' }}
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
