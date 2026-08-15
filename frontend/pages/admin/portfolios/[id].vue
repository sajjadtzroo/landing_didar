<script setup lang="ts">
import {
  ArrowDown, ArrowRight, ArrowUp, Plus, Trash2, Upload, X,
} from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { AdminPortfolio, Product } from '~/types'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const id = route.params.id as string

const { data: portfolio } = await useAsyncData(`admin-portfolio-${id}`, () =>
  apiFetch<AdminPortfolio>(`/admin/portfolios/${id}`),
)
const { data: products } = await useAsyncData('admin-all-products', () =>
  apiFetch<Product[]>('/admin/products'),
)
if (!portfolio.value) {
  throw createError({ statusCode: 404, statusMessage: 'Portfolio not found', fatal: true })
}

const productById = computed(() =>
  Object.fromEntries((products.value ?? []).map((p) => [p.id, p])) as Record<string, Product>,
)

// --- Editable state ---
const raw = (portfolio.value.content || {}) as any
const meta = reactive({
  name: portfolio.value.name || '',
  slug: portfolio.value.slug || '',
  cover_image_url: portfolio.value.cover_image_url || '',
  is_active: portfolio.value.is_active ?? true,
  sort_order: portfolio.value.sort_order ?? 0,
})
const content = reactive({
  groups: (Array.isArray(raw.groups) ? raw.groups : []).map((g: any) => ({
    title: g?.title || '', eyebrow: g?.eyebrow || '', description: g?.description || '',
    product_ids: Array.isArray(g?.product_ids) ? [...g.product_ids] : [],
  })),
})

// --- List helpers ---
function move(arr: any[], i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= arr.length) return
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}
function removeAt(arr: any[], i: number) {
  arr.splice(i, 1)
}
function addGroup() {
  content.groups.push({ title: 'گروه جدید', eyebrow: '', description: '', product_ids: [] })
}
function availableFor(g: any): Product[] {
  return (products.value ?? []).filter((p) => !g.product_ids.includes(p.id))
}
function addProduct(g: any, pid: string) {
  if (pid && !g.product_ids.includes(pid)) g.product_ids.push(pid)
}

// --- Cover upload ---
const { upload } = useAdminUpload()
const uploading = ref(false)
async function pickCover(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  try {
    meta.cover_image_url = await upload(file)
  } catch {
    alert('بارگذاری فایل ناموفق بود.')
  } finally {
    uploading.value = false
    ;(e.target as HTMLInputElement).value = ''
  }
}

// --- Save / delete ---
const saving = ref(false)
const saved = ref(false)
const saveError = ref('')
async function save() {
  saving.value = true
  saved.value = false
  saveError.value = ''
  try {
    await apiFetch(`/admin/portfolios/${id}`, {
      method: 'PATCH',
      body: {
        name: meta.name,
        slug: meta.slug,
        cover_image_url: meta.cover_image_url || null,
        is_active: meta.is_active,
        sort_order: Number(meta.sort_order) || 0,
        content: JSON.parse(JSON.stringify(content)),
      },
    })
    saved.value = true
  } catch (e: any) {
    saveError.value = e?.data?.detail || 'ذخیره ناموفق بود.'
  } finally {
    saving.value = false
  }
}
async function removePortfolio() {
  if (!confirm('این پورتفولیو حذف شود؟')) return
  await apiFetch(`/admin/portfolios/${id}`, { method: 'DELETE' })
  await navigateTo('/admin/portfolios')
}
</script>

<template>
  <div class="pb-28">
    <!-- Header -->
    <div class="mb-6 flex flex-wrap items-center gap-3">
      <NuxtLink
        to="/admin/portfolios"
        class="flex h-10 w-10 items-center justify-center text-ink-muted hover:text-ink"
        aria-label="بازگشت"
      >
        <ArrowRight :size="18" />
      </NuxtLink>
      <div class="min-w-0 flex-1">
        <h1 class="truncate text-2xl font-medium">{{ meta.name || 'ویرایش پورتفولیو' }}</h1>
        <p class="tnum text-xs text-ink-muted" dir="ltr">{{ portfolio?.slug }}</p>
      </div>
      <button
        class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger"
        aria-label="حذف پورتفولیو"
        @click="removePortfolio"
      >
        <Trash2 :size="16" />
      </button>
    </div>

    <div class="space-y-6">
      <!-- Basics -->
      <section class="admin-card space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-medium">مشخصات</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="meta.is_active" type="checkbox" class="h-4 w-4" /> فعال (نمایش در فروشگاه)
          </span>
        </div>
        <FormField label="نام" v-slot="{ id: fid }">
          <input :id="fid" v-model="meta.name" class="form-control" />
        </FormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <FormField label="اسلاگ (انگلیسی، یکتا)" v-slot="{ id: fid }">
            <input :id="fid" v-model="meta.slug" dir="ltr" class="form-control" />
          </FormField>
          <FormField label="ترتیب نمایش (کوچک‌تر = بالاتر)" v-slot="{ id: fid }">
            <input :id="fid" v-model="meta.sort_order" type="number" dir="ltr" class="form-control" />
          </FormField>
        </div>

        <!-- Cover image -->
        <div>
          <p class="mb-1.5 text-sm">تصویر کاور (اختیاری)</p>
          <input v-model="meta.cover_image_url" dir="ltr" class="form-control" placeholder="/media/cover.jpg" aria-label="آدرس تصویر کاور" />
          <label class="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs text-gold-text hover:underline">
            <Upload :size="14" />
            {{ uploading ? 'در حال بارگذاری…' : 'بارگذاری تصویر' }}
            <input type="file" accept="image/*" class="hidden" @change="pickCover" />
          </label>
          <NuxtImg v-if="meta.cover_image_url" :src="meta.cover_image_url" alt="" class="mt-2 h-28 w-full object-cover" />
        </div>
      </section>

      <!-- Product groups -->
      <section class="admin-card space-y-4">
        <h2 class="text-lg font-medium">گروه‌های محصول</h2>

        <div v-for="(g, gi) in content.groups" :key="gi" class="admin-subcard space-y-3 p-4">
          <div class="flex items-center gap-2">
            <p class="flex-1 text-sm font-medium">گروه {{ gi + 1 }}</p>
            <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="gi === 0" aria-label="بالا" @click="move(content.groups, gi, -1)"><ArrowUp :size="15" /></button>
            <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="gi === content.groups.length - 1" aria-label="پایین" @click="move(content.groups, gi, 1)"><ArrowDown :size="15" /></button>
            <button class="text-ink-muted hover:text-danger" aria-label="حذف گروه" @click="removeAt(content.groups, gi)"><Trash2 :size="15" /></button>
          </div>
          <div class="grid gap-3 sm:grid-cols-3">
            <input v-model="g.title" class="form-control" placeholder="عنوان گروه" aria-label="عنوان گروه" />
            <input v-model="g.eyebrow" class="form-control" placeholder="روتیتر" aria-label="روتیتر" />
            <input v-model="g.description" class="form-control" placeholder="توضیح کوتاه" aria-label="توضیح کوتاه" />
          </div>

          <!-- Selected products (ordered) -->
          <ul v-if="g.product_ids.length" class="space-y-1.5">
            <li
              v-for="(pid, pi) in g.product_ids"
              :key="pid"
              class="corner-soft flex items-center gap-2 border border-white/60 bg-cream-bright/70 p-2 text-sm"
            >
              <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="pi === 0" aria-label="بالا" @click="move(g.product_ids, pi, -1)"><ArrowUp :size="13" /></button>
              <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="pi === g.product_ids.length - 1" aria-label="پایین" @click="move(g.product_ids, pi, 1)"><ArrowDown :size="13" /></button>
              <span class="min-w-0 flex-1 truncate">{{ productById[pid]?.name || pid }}</span>
              <button class="text-ink-muted hover:text-danger" aria-label="حذف" @click="removeAt(g.product_ids, pi)"><X :size="14" /></button>
            </li>
          </ul>
          <p v-else class="text-xs text-ink-muted">محصولی در این گروه نیست.</p>

          <select
            class="form-control"
            @change="addProduct(g, ($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''"
          >
            <option value="">افزودن محصول…</option>
            <option v-for="p in availableFor(g)" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <button class="flex items-center gap-2 text-sm text-gold-text hover:underline" @click="addGroup">
          <Plus :size="15" /> افزودن گروه
        </button>
      </section>
    </div>

    <!-- Sticky save bar -->
    <div class="fixed inset-x-0 bottom-0 z-40 border-t border-white/40 bg-cream-bright/70 px-5 py-3 backdrop-blur-xl lg:pe-72">
      <div class="mx-auto flex max-w-4xl items-center gap-3">
        <span v-if="saved" class="text-sm text-success">ذخیره شد ✓</span>
        <span v-if="saveError" class="text-sm text-danger">{{ saveError }}</span>
        <div class="flex-1" />
        <button
          class="flex h-12 items-center justify-center bg-navy px-8 text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'در حال ذخیره…' : 'ذخیره تغییرات' }}
        </button>
      </div>
    </div>
  </div>
</template>
