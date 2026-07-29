<script setup lang="ts">
import { ArrowDown, ArrowUp, Pencil, Plus, Trash2, Upload } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { Product } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

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
  price: '' as string | number,
  onRequest: false,
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
    price: p.price ?? '',
    onRequest: p.price == null,
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
    price: form.onRequest || form.price === '' ? null : Number(form.price),
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
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-medium">محصولات</h1>
      <button
        class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        @click="startCreate"
      >
        <Plus :size="16" /> محصول جدید
      </button>
    </div>

    <ul class="space-y-3">
      <li
        v-for="(p, i) in products"
        :key="p.id"
        class="flex items-center gap-4 border border-line bg-surface-raised p-3"
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
            {{ p.sku }} · {{ formatPrice(p.price) ?? 'استعلام قیمت' }}
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
        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.onRequest" type="checkbox" /> استعلام قیمت (بدون قیمت ثابت)
        </label>
        <FormField v-if="!form.onRequest" label="قیمت (تومان)" v-slot="{ id }">
          <input :id="id" v-model="form.price" type="number" class="form-control" />
        </FormField>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox" /> فعال</label>
      </div>
      <template #footer>
        <button class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold" @click="save">
          ذخیره
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
