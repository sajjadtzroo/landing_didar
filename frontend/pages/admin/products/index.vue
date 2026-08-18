<script setup lang="ts">
import { ArrowDown, ArrowUp, FileSpreadsheet, ImageDown, Pencil, Plus, Trash2, Upload } from 'lucide-vue-next'
import { onBeforeUnmount, reactive, ref } from 'vue'
import type { ImportJob, Product } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const { data: products, refresh } = await useAsyncData('admin-products', () =>
  apiFetch<Product[]>('/admin/products'),
)

const blank = () => ({
  id: '',
  name: '',
  slug: '',
  sku: '',
  weight_grams: '',
  karat: 18,
  ojrat_percent: '' as string | number,
  category: 'daily' as 'daily' | 'lux_daily' | 'luxury' | 'watch',
  supplier: '',
  product_status: 'sellable' as 'sellable' | 'sample' | 'not_for_sale',
  warrantable: true,
  is_active: true,
})
const form = reactive(blank())
const editing = ref(false)
const panelOpen = ref(false)

function startCreate() {
  Object.assign(form, blank())
  editing.value = false
  panelOpen.value = true
}
function startEdit(p: Product) {
  Object.assign(form, {
    id: p.id,
    name: p.name,
    slug: p.slug ?? '',
    sku: p.sku,
    weight_grams: p.weight_grams ?? '',
    karat: p.karat ?? 18,
    ojrat_percent: p.ojrat_percent ?? '',
    category: p.category ?? 'daily',
    supplier: p.supplier ?? '',
    product_status: p.product_status ?? 'sellable',
    warrantable: p.warrantable ?? true,
    is_active: p.is_active,
  })
  editing.value = true
  panelOpen.value = true
}

async function save() {
  const body = {
    name: form.name,
    slug: form.slug || null,
    sku: form.sku,
    weight_grams: form.weight_grams === '' ? null : Number(form.weight_grams),
    karat: form.karat ? Number(form.karat) : null,
    ojrat_percent: form.ojrat_percent === '' ? null : Number(form.ojrat_percent),
    category: form.category,
    supplier: form.supplier || null,
    product_status: form.product_status,
    warrantable: form.warrantable,
    is_active: form.is_active,
    sort_order: editing.value
      ? undefined
      : (products.value?.length ?? 0),
  }
  if (editing.value) {
    await apiFetch(`/admin/products/${form.id}`, { method: 'PATCH', body })
  } else {
    await apiFetch('/admin/products', { method: 'POST', body })
  }
  panelOpen.value = false
  await refresh()
}

async function toggleActive(p: Product) {
  await apiFetch(`/admin/products/${p.id}`, {
    method: 'PATCH',
    body: { is_active: !p.is_active },
  })
  await refresh()
}

async function remove(p: Product) {
  if (!confirm(`حذف «${p.name}»؟`)) return
  await apiFetch(`/admin/products/${p.id}`, { method: 'DELETE' })
  await refresh()
}

async function uploadImage(p: Product, e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  await apiFetch(`/admin/products/${p.id}/image`, { method: 'POST', body: fd })
  await refresh()
}

// --- Bulk CSV import (background job with progress polling) ---
const importOpen = ref(false)
const importFile = ref<File | null>(null)
const importSyncImages = ref(false)
const importJob = ref<ImportJob | null>(null)
const importError = ref('')
const importBusy = ref(false)
let pollTimer: ReturnType<typeof setInterval> | undefined

function startImport() {
  importFile.value = null
  importJob.value = null
  importError.value = ''
  importOpen.value = true
}
function onImportFile(e: Event) {
  importFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
}
function templateUrl() {
  return `${useApiBase()}/admin/products/import/template`
}

async function uploadImport() {
  if (!importFile.value) return
  importBusy.value = true
  importError.value = ''
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    fd.append('sync_images', String(importSyncImages.value))
    const res = await apiFetch<{ job_id: string }>('/admin/products/import', {
      method: 'POST',
      body: fd,
    })
    pollJob(res.job_id)
  } catch (e: any) {
    importError.value = e?.data?.detail || 'بارگذاری ناموفق بود.'
    importBusy.value = false
  }
}

function pollJob(jobId: string) {
  clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    importJob.value = await apiFetch<ImportJob>(`/admin/products/import/${jobId}`)
    if (importJob.value.status === 'done' || importJob.value.status === 'failed') {
      clearInterval(pollTimer)
      importBusy.value = false
      await refresh()
    }
  }, 700)
}
onBeforeUnmount(() => clearInterval(pollTimer))

// Standalone MinIO photo sync ({sku}/ folders), same job machinery.
const syncBusy = ref(false)
async function syncImagesNow() {
  syncBusy.value = true
  try {
    const res = await apiFetch<{ job_id: string }>('/admin/products/sync-images', { method: 'POST' })
    importJob.value = null
    importOpen.value = true
    importFile.value = null
    pollJob(res.job_id)
  } catch {
    syncBusy.value = false
  }
}

// ponytail: keyboard-accessible up/down reorder instead of mouse-only drag —
// swaps sort_order with the neighbour. Add HTML5 drag later if truly needed.
async function move(index: number, dir: -1 | 1) {
  const list = products.value
  if (!list) return
  const other = index + dir
  if (other < 0 || other >= list.length) return
  const a = list[index]
  const b = list[other]
  await Promise.all([
    apiFetch(`/admin/products/${a.id}`, { method: 'PATCH', body: { sort_order: b.sort_order } }),
    apiFetch(`/admin/products/${b.id}`, { method: 'PATCH', body: { sort_order: a.sort_order } }),
  ])
  await refresh()
}
</script>

<template>
  <div>
    <AdminPageHeader title="محصولات">
      <button
        class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold disabled:opacity-60"
        :disabled="syncBusy"
        @click="syncImagesNow"
      >
        <ImageDown :size="16" /> همگام‌سازی تصاویر
      </button>
      <button
        class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold"
        @click="startImport"
      >
        <FileSpreadsheet :size="16" /> ورود گروهی (CSV)
      </button>
      <button
        class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        @click="startCreate"
      >
        <Plus :size="16" /> محصول جدید
      </button>
    </AdminPageHeader>

    <ul class="space-y-3">
      <li
        v-for="(p, i) in products"
        :key="p.id"
        class="admin-card admin-card--hover flex items-center gap-4 p-3"
        :class="!p.is_active ? 'opacity-60' : ''"
      >
        <div class="flex flex-col">
          <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="i === 0"
            aria-label="بالا" @click="move(i, -1)"><ArrowUp :size="16" /></button>
          <button class="text-ink-muted hover:text-ink disabled:opacity-30"
            :disabled="i === (products?.length ?? 0) - 1" aria-label="پایین" @click="move(i, 1)">
            <ArrowDown :size="16" />
          </button>
        </div>

        <div class="h-14 w-14 shrink-0 overflow-hidden bg-media-surface">
          <NuxtImg v-if="p.image_url" :src="p.image_url" :alt="p.name" class="h-full w-full object-cover" width="56" height="56" />
        </div>

        <div class="min-w-0 flex-1">
          <p class="truncate text-ink">{{ p.name }}</p>
          <p class="tnum text-xs text-ink-muted">
            {{ p.sku }}
            <template v-if="p.weight_grams"> · {{ toFa(Number(p.weight_grams)) }} گرم</template>
            <template v-if="p.ojrat_percent"> · اجرت {{ toFa(Number(p.ojrat_percent)) }}٪</template>
          </p>
        </div>

        <label class="flex h-11 w-11 cursor-pointer items-center justify-center text-ink-muted hover:text-gold-text" aria-label="بارگذاری تصویر">
          <Upload :size="16" />
          <input type="file" accept="image/*" class="hidden" @change="uploadImage(p, $event)" />
        </label>
        <button class="flex h-11 items-center px-2 text-xs" @click="toggleActive(p)">
          {{ p.is_active ? 'فعال' : 'غیرفعال' }}
        </button>
        <button class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-gold-text" aria-label="ویرایش" @click="startEdit(p)">
          <Pencil :size="16" />
        </button>
        <button class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger" aria-label="حذف" @click="remove(p)">
          <Trash2 :size="16" />
        </button>
      </li>
    </ul>

    <BaseSheet v-model="panelOpen" :title="editing ? 'ویرایش محصول' : 'محصول جدید'">
      <div class="space-y-4">
        <FormField label="نام" v-slot="{ id }"><input :id="id" v-model="form.name" class="form-control" /></FormField>
        <FormField label="نامک (slug — آدرس صفحه، مثال: atrin-necklace)" v-slot="{ id }">
          <input :id="id" v-model="form.slug" dir="ltr" class="form-control" placeholder="atrin-necklace" />
        </FormField>
        <FormField label="کد (SKU)" v-slot="{ id }"><input :id="id" v-model="form.sku" class="form-control" /></FormField>
        <FormField label="وزن (گرم)" v-slot="{ id }"><input :id="id" v-model="form.weight_grams" type="number" step="0.01" class="form-control" /></FormField>
        <FormField label="عیار" v-slot="{ id }"><input :id="id" v-model="form.karat" type="number" class="form-control" /></FormField>
        <FormField label="اجرت (٪)" v-slot="{ id }"><input :id="id" v-model="form.ojrat_percent" type="number" step="0.5" min="0" max="100" class="form-control" /></FormField>
        <FormField label="دسته‌بندی" v-slot="{ id }">
          <select :id="id" v-model="form.category" class="form-control">
            <option value="daily">روزمره</option>
            <option value="lux_daily">لوکس روزمره</option>
            <option value="luxury">لوکس</option>
            <option value="watch">ساعت</option>
          </select>
        </FormField>
        <FormField label="تأمین‌کننده / سازنده (اختیاری)" v-slot="{ id }">
          <input :id="id" v-model="form.supplier" class="form-control" />
        </FormField>
        <FormField label="وضعیت فروش" v-slot="{ id }">
          <select :id="id" v-model="form.product_status" class="form-control">
            <option value="sellable">قابل فروش</option>
            <option value="sample">نمونه (غیرقابل سفارش)</option>
            <option value="not_for_sale">غیرقابل فروش (پنهان)</option>
          </select>
        </FormField>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.warrantable" type="checkbox" /> دارای گارانتی</label>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox" /> فعال</label>
      </div>
      <template #footer>
        <button class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold" @click="save">
          ذخیره
        </button>
      </template>
    </BaseSheet>

    <!-- Bulk CSV import sheet -->
    <BaseSheet v-model="importOpen" title="ورود گروهی محصولات">
      <!-- Job progress / result -->
      <div v-if="importJob" class="space-y-4">
        <div>
          <div class="mb-1 flex justify-between text-sm">
            <span>
              {{ importJob.status === 'done' ? 'انجام شد' : importJob.status === 'failed' ? 'ناموفق' : 'در حال پردازش…' }}
            </span>
            <span v-if="importJob.total" class="tnum text-ink-muted">
              {{ toFa(importJob.processed) }} / {{ toFa(importJob.total) }}
            </span>
          </div>
          <div class="h-2 w-full bg-surface-soft">
            <div
              class="h-2 transition-all duration-300"
              :class="importJob.status === 'failed' ? 'bg-danger' : 'bg-gold'"
              :style="{ width: importJob.total ? `${(importJob.processed / importJob.total) * 100}%` : importJob.status === 'done' ? '100%' : '30%' }"
            />
          </div>
        </div>

        <div v-if="importJob.status === 'done'" class="corner-soft border border-line bg-success-soft p-3 text-sm text-success">
          <span class="tnum">{{ toFa(importJob.created_count) }}</span> محصول جدید ·
          <span class="tnum">{{ toFa(importJob.updated_count) }}</span> به‌روزرسانی
          <template v-if="importJob.result?.photos?.photos != null">
            · <span class="tnum">{{ toFa(importJob.result.photos.photos) }}</span> عکس از MinIO
          </template>
          <template v-else-if="importJob.result?.photos != null && importJob.kind === 'image_sync'">
            · <span class="tnum">{{ toFa(importJob.result.photos) }}</span> عکس از MinIO
          </template>
        </div>

        <div v-if="importJob.errors?.length" class="max-h-52 overflow-y-auto border border-line">
          <p class="border-b border-line bg-danger-soft p-2 text-xs text-danger">
            {{ toFa(importJob.errors.length) }} ردیف خطا (بقیه ردیف‌ها ثبت شدند)
          </p>
          <ul class="divide-y divide-line text-xs">
            <li v-for="(e, i) in importJob.errors" :key="i" class="flex gap-2 p-2">
              <span class="tnum shrink-0 text-ink-muted">ردیف {{ toFa(e.row) }}</span>
              <span>{{ e.error }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Upload form -->
      <div v-else class="space-y-4">
        <p class="text-sm leading-6 text-ink-muted">
          فایل CSV با ستون‌های الگو بارگذاری کنید. ردیف‌ها با «کد (SKU)» تطبیق داده می‌شوند —
          کد جدید ساخته می‌شود، کد تکراری به‌روزرسانی می‌شود و سلول خالی یعنی بدون تغییر.
          اعداد فارسی و برچسب‌های فارسی (روزمره / لوکس / نمونه / بله…) پذیرفته می‌شوند.
        </p>
        <a :href="templateUrl()" class="text-sm text-gold-text underline underline-offset-4 hover:no-underline" download>
          دانلود فایل الگو (CSV)
        </a>
        <FormField label="فایل CSV" v-slot="{ id }">
          <input :id="id" type="file" accept=".csv,text/csv" class="form-control py-3.5" @change="onImportFile" />
        </FormField>
        <label class="flex items-start gap-2 text-sm">
          <input v-model="importSyncImages" type="checkbox" class="mt-1" />
          <span>
            دریافت عکس‌ها از MinIO پس از ورود
            <span class="block text-xs text-ink-muted">عکس هر محصول باید در پوشه‌ای هم‌نام با SKU آن باشد (مثل <span class="tnum" dir="ltr">NK-101/1.jpg</span>).</span>
          </span>
        </label>
        <p v-if="importError" class="text-sm text-danger">{{ importError }}</p>
      </div>

      <template #footer>
        <button
          v-if="!importJob"
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="!importFile || importBusy"
          @click="uploadImport"
        >
          {{ importBusy ? 'در حال بارگذاری…' : 'شروع ورود' }}
        </button>
        <button
          v-else-if="importJob.status === 'done' || importJob.status === 'failed'"
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold"
          @click="importOpen = false"
        >
          بستن
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
