<script setup lang="ts">
import { BadgeCheck, Copy, Download, Plus, Search, Trash2 } from 'lucide-vue-next'
import { reactive, ref, watch } from 'vue'
import type { Product, ProductSerial, SerialListResponse } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const STATUS_LABEL: Record<ProductSerial['status'], string> = {
  in_stock: 'موجود',
  sold: 'فروخته‌شده',
  revoked: 'باطل‌شده',
}
const STATUS_CLASS: Record<ProductSerial['status'], string> = {
  in_stock: 'bg-surface-soft text-ink-muted',
  sold: 'bg-success-soft text-success',
  revoked: 'bg-danger-soft text-danger',
}

const filters = reactive({ q: '', product_id: '', status: '', page: 1 })

function query() {
  const p = new URLSearchParams()
  if (filters.q) p.set('q', filters.q)
  if (filters.product_id) p.set('product_id', filters.product_id)
  if (filters.status) p.set('status', filters.status)
  p.set('page', String(filters.page))
  return p.toString()
}

const { data: products } = await useAsyncData('admin-products-min', () =>
  apiFetch<Product[]>('/admin/products'),
)
const { data, refresh } = await useAsyncData(
  'admin-serials',
  () => apiFetch<SerialListResponse>(`/admin/serials?${query()}`),
  { watch: [() => filters.page] },
)
const debounced = useDebounceFn(() => {
  filters.page = 1
  refresh()
}, 300)
watch(() => [filters.q, filters.product_id, filters.status], debounced)

// --- Generate ---
const panelOpen = ref(false)
const gen = reactive({ product_id: '', quantity: 20 })
const generating = ref(false)
const lastBatch = ref<ProductSerial[] | null>(null)

function startGenerate() {
  gen.product_id = products.value?.[0]?.id ?? ''
  gen.quantity = 20
  lastBatch.value = null
  panelOpen.value = true
}
async function generate() {
  if (!gen.product_id || gen.quantity < 1) return
  generating.value = true
  try {
    lastBatch.value = await apiFetch<ProductSerial[]>('/admin/serials/generate', {
      method: 'POST',
      body: { product_id: gen.product_id, quantity: Number(gen.quantity) },
    })
    await refresh()
  } finally {
    generating.value = false
  }
}

async function setStatus(s: ProductSerial, status: string) {
  await apiFetch(`/admin/serials/${s.id}`, { method: 'PATCH', body: { status } })
  await refresh()
}
async function remove(s: ProductSerial) {
  if (!confirm(`حذف سریال ${s.code}؟`)) return
  await apiFetch(`/admin/serials/${s.id}`, { method: 'DELETE' })
  await refresh()
}
function copy(code: string) {
  navigator.clipboard?.writeText(code)
}
function exportCsv(batchId?: string) {
  const p = batchId ? `batch_id=${batchId}` : query()
  window.open(`${useApiBase()}/admin/serials/export?${p}`, '_blank')
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <AdminPageHeader title="سریال‌ها / اصالت" subtitle="کد اصالت هر قطعه؛ مشتری با آن اصل بودن را بررسی می‌کند.">
      <button
        class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold"
        @click="exportCsv()"
      >
        <Download :size="16" /> خروجی CSV
      </button>
      <button
        class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        @click="startGenerate"
      >
        <Plus :size="16" /> تولید سریال
      </button>
    </AdminPageHeader>

    <!-- Filters -->
    <div class="mb-3 grid gap-3 sm:grid-cols-3">
      <div class="relative">
        <Search :size="16" class="absolute inset-y-0 end-3 my-auto text-ink-muted" />
        <input v-model="filters.q" type="search" placeholder="جستجوی کد سریال" class="form-control pe-9" />
      </div>
      <select v-model="filters.product_id" class="form-control">
        <option value="">همه محصولات</option>
        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <select v-model="filters.status" class="form-control">
        <option value="">همه وضعیت‌ها</option>
        <option value="in_stock">موجود</option>
        <option value="sold">فروخته‌شده</option>
        <option value="revoked">باطل‌شده</option>
      </select>
    </div>

    <p v-if="data" class="tnum mb-3 text-xs text-ink-muted">{{ toFa(data.total) }} سریال</p>

    <!-- Table -->
    <div class="hidden overflow-x-auto border border-line md:block">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">کد سریال</th>
            <th class="p-3 text-start">محصول</th>
            <th class="p-3 text-start">سفارش</th>
            <th class="p-3 text-start">وضعیت</th>
            <th class="p-3 text-start">بازدید اصالت</th>
            <th class="p-3 text-start">تاریخ صدور</th>
            <th class="p-3 text-start"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in data?.items" :key="s.id" class="border-t border-line hover:bg-surface-soft">
            <td class="p-3">
              <button class="inline-flex items-center gap-1.5 hover:text-gold-text" :title="'کپی'" @click="copy(s.code)">
                <span class="tnum font-medium text-gold-text" dir="ltr">{{ s.code }}</span>
                <Copy :size="13" class="opacity-50" />
              </button>
            </td>
            <td class="p-3">{{ s.product_name }}</td>
            <td class="tnum p-3 text-ink-muted" dir="ltr">{{ s.order_reference ?? '—' }}</td>
            <td class="p-3">
              <select
                class="border-0 bg-transparent px-2 py-1 text-xs"
                :class="STATUS_CLASS[s.status]"
                :value="s.status"
                @change="setStatus(s, ($event.target as HTMLSelectElement).value)"
              >
                <option value="in_stock">{{ STATUS_LABEL.in_stock }}</option>
                <option value="sold">{{ STATUS_LABEL.sold }}</option>
                <option value="revoked">{{ STATUS_LABEL.revoked }}</option>
              </select>
            </td>
            <td class="tnum p-3" :class="s.verify_count ? 'text-ink' : 'text-ink-muted'">
              {{ toFa(s.verify_count) }}
            </td>
            <td class="tnum p-3 text-ink-muted">{{ faDate(s.created_at) }}</td>
            <td class="p-3 text-end">
              <button class="text-ink-muted hover:text-danger" aria-label="حذف" @click="remove(s)">
                <Trash2 :size="16" />
              </button>
            </td>
          </tr>
          <tr v-if="!data?.items?.length">
            <td colspan="7" class="p-12 text-center text-ink-muted">سریالی یافت نشد.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile cards -->
    <div class="space-y-3 md:hidden">
      <div v-for="s in data?.items" :key="s.id" class="admin-card p-4">
        <div class="flex items-center justify-between gap-2">
          <button class="tnum inline-flex items-center gap-1.5 font-medium text-gold-text" dir="ltr" @click="copy(s.code)">
            {{ s.code }} <Copy :size="13" class="opacity-50" />
          </button>
          <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[s.status]">{{ STATUS_LABEL[s.status] }}</span>
        </div>
        <p class="mt-2 text-sm">{{ s.product_name }}</p>
        <div class="mt-1 flex items-center justify-between text-xs text-ink-muted">
          <span class="tnum">صدور: {{ faDate(s.created_at) }}</span>
          <span class="tnum">بازدید اصالت: {{ toFa(s.verify_count) }}</span>
        </div>
      </div>
      <p v-if="!data?.items?.length" class="py-12 text-center text-ink-muted">سریالی یافت نشد.</p>
    </div>

    <!-- Pagination -->
    <div v-if="data && data.total > data.page_size" class="mt-6 flex items-center justify-center gap-4">
      <button class="h-10 border border-line px-4 text-sm disabled:opacity-50" :disabled="filters.page <= 1" @click="filters.page--">قبلی</button>
      <span class="tnum text-sm text-ink-muted">صفحه {{ toFa(filters.page) }}</span>
      <button class="h-10 border border-line px-4 text-sm disabled:opacity-50" :disabled="filters.page * data.page_size >= data.total" @click="filters.page++">بعدی</button>
    </div>

    <!-- Generate sheet -->
    <BaseSheet v-model="panelOpen" title="تولید سریال">
      <div v-if="!lastBatch" class="space-y-4">
        <FormField label="محصول" v-slot="{ id }">
          <select :id="id" v-model="gen.product_id" class="form-control">
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </FormField>
        <FormField label="تعداد" v-slot="{ id }">
          <input :id="id" v-model.number="gen.quantity" type="number" min="1" max="5000" class="form-control" />
        </FormField>
        <p class="text-xs text-ink-muted">برای هر قطعه یک کد یکتا ساخته می‌شود. مشخصات محصول در لحظهٔ تولید ثبت (اسنپ‌شات) می‌شود.</p>
      </div>

      <!-- Result -->
      <div v-else class="space-y-3">
        <p class="text-sm text-success">{{ toFa(lastBatch.length) }} سریال ساخته شد.</p>
        <div class="max-h-64 overflow-y-auto border border-line bg-surface-soft p-3">
          <p v-for="s in lastBatch" :key="s.id" class="tnum text-sm text-ink" dir="ltr">{{ s.code }}</p>
        </div>
      </div>

      <template #footer>
        <button
          v-if="!lastBatch"
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="generating || !gen.product_id"
          @click="generate"
        >
          {{ generating ? 'در حال تولید…' : 'تولید' }}
        </button>
        <button
          v-else
          class="flex h-[58px] w-full items-center justify-center gap-2 bg-navy text-base font-medium text-white hover:bg-gold"
          @click="exportCsv(lastBatch[0]?.batch_id)"
        >
          <Download :size="18" /> دانلود CSV این دسته
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
