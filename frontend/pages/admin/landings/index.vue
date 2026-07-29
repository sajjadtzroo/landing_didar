<script setup lang="ts">
import { ArrowDown, ArrowUp, ExternalLink, Pencil, Plus, X } from 'lucide-vue-next'
import { computed, reactive, ref } from 'vue'
import type { AdminLanding, Product } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const { data: landings, refresh } = await useAsyncData('admin-landings', () =>
  apiFetch<AdminLanding[]>('/admin/landings'),
)
const { data: products } = await useAsyncData('admin-all-products', () =>
  apiFetch<Product[]>('/admin/products'),
)

const productById = computed(() =>
  Object.fromEntries((products.value ?? []).map((p) => [p.id, p])),
)

const panelOpen = ref(false)
const editing = ref<AdminLanding | null>(null)
const form = reactive({ title: '', hero_video_url: '', hero_poster_url: '' })
const selected = ref<string[]>([]) // ordered product ids assigned to this landing

const selectedProducts = computed(() =>
  selected.value.map((id) => productById.value[id]).filter(Boolean) as Product[],
)
const available = computed(() =>
  (products.value ?? []).filter((p) => !selected.value.includes(p.id)),
)

function startEdit(ln: AdminLanding) {
  editing.value = ln
  form.title = ln.title
  form.hero_video_url = ln.hero_video_url ?? ''
  form.hero_poster_url = ln.hero_poster_url ?? ''
  selected.value = [...ln.product_ids]
  panelOpen.value = true
}

function add(id: string) {
  selected.value = [...selected.value, id]
}
function removeSel(id: string) {
  selected.value = selected.value.filter((x) => x !== id)
}
function move(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= selected.value.length) return
  const arr = [...selected.value]
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
  selected.value = arr
}

async function save() {
  if (!editing.value) return
  await apiFetch(`/admin/landings/${editing.value.id}`, {
    method: 'PATCH',
    body: {
      title: form.title,
      hero_video_url: form.hero_video_url || null,
      hero_poster_url: form.hero_poster_url || null,
    },
  })
  await apiFetch(`/admin/landings/${editing.value.id}/products`, {
    method: 'PUT',
    body: { product_ids: selected.value },
  })
  panelOpen.value = false
  await refresh()
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-medium">صفحات فرود</h1>
      <p class="mt-1 text-sm text-ink-muted">
        سه صفحه فرود ثابت. برای هرکدام ویدیوی هیرو و محصولات نمایش‌داده‌شده را تنظیم کنید.
      </p>
    </div>

    <ul class="space-y-3">
      <li
        v-for="ln in landings"
        :key="ln.id"
        class="flex items-center gap-4 border border-line bg-surface-raised p-4"
      >
        <div class="min-w-0 flex-1">
          <p class="text-ink">{{ ln.title }}</p>
          <p class="tnum text-xs text-ink-muted" dir="ltr">
            /l/{{ ln.slug }} · {{ toFa(ln.product_ids.length) }} محصول
          </p>
        </div>
        <a
          :href="`/l/${ln.slug}`"
          target="_blank"
          rel="noopener"
          class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-gold-text"
          aria-label="پیش‌نمایش"
        >
          <ExternalLink :size="16" />
        </a>
        <button
          class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
          @click="startEdit(ln)"
        >
          <Pencil :size="16" /> ویرایش
        </button>
      </li>
    </ul>

    <BaseSheet v-model="panelOpen" :title="editing ? `ویرایش: ${editing.title}` : ''">
      <div class="space-y-5">
        <FormField label="عنوان" v-slot="{ id }">
          <input :id="id" v-model="form.title" class="form-control" />
        </FormField>
        <FormField label="آدرس ویدیوی هیرو (URL یا مسیر فایل در public/media)" v-slot="{ id }">
          <input
            :id="id"
            v-model="form.hero_video_url"
            dir="ltr"
            class="form-control"
            placeholder="/media/hero.mp4"
          />
        </FormField>
        <FormField label="آدرس تصویر پوستر (نمایش هنگام کاهش انیمیشن)" v-slot="{ id }">
          <input
            :id="id"
            v-model="form.hero_poster_url"
            dir="ltr"
            class="form-control"
            placeholder="/media/hero-poster.jpg"
          />
        </FormField>

        <!-- Assigned products (ordered) -->
        <div>
          <p class="mb-2 text-sm font-medium">
            محصولات این صفحه ({{ toFa(selectedProducts.length) }})
          </p>
          <ul v-if="selectedProducts.length" class="space-y-2">
            <li
              v-for="(p, i) in selectedProducts"
              :key="p.id"
              class="flex items-center gap-2 border border-line bg-surface p-2"
            >
              <div class="flex flex-col">
                <button
                  class="text-ink-muted hover:text-ink disabled:opacity-30"
                  :disabled="i === 0"
                  aria-label="بالا"
                  @click="move(i, -1)"
                >
                  <ArrowUp :size="14" />
                </button>
                <button
                  class="text-ink-muted hover:text-ink disabled:opacity-30"
                  :disabled="i === selectedProducts.length - 1"
                  aria-label="پایین"
                  @click="move(i, 1)"
                >
                  <ArrowDown :size="14" />
                </button>
              </div>
              <span class="tnum w-6 text-center text-xs text-ink-muted">{{ toFa(i + 1) }}</span>
              <p class="min-w-0 flex-1 truncate text-sm">{{ p.name }}</p>
              <button
                class="flex h-9 w-9 items-center justify-center text-ink-muted hover:text-danger"
                aria-label="حذف از صفحه"
                @click="removeSel(p.id)"
              >
                <X :size="15" />
              </button>
            </li>
          </ul>
          <p v-else class="text-xs text-ink-muted">هیچ محصولی انتخاب نشده است.</p>
        </div>

        <!-- Available products -->
        <div v-if="available.length">
          <p class="mb-2 text-sm font-medium text-ink-muted">افزودن محصول</p>
          <ul class="space-y-2">
            <li
              v-for="p in available"
              :key="p.id"
              class="flex items-center gap-2 border border-line border-dashed p-2"
              :class="!p.is_active ? 'opacity-60' : ''"
            >
              <button
                class="flex h-9 w-9 items-center justify-center text-ink-muted hover:text-gold-text"
                aria-label="افزودن"
                @click="add(p.id)"
              >
                <Plus :size="15" />
              </button>
              <p class="min-w-0 flex-1 truncate text-sm">{{ p.name }}</p>
              <span v-if="!p.is_active" class="text-xs text-ink-muted">غیرفعال</span>
            </li>
          </ul>
        </div>
      </div>

      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold"
          @click="save"
        >
          ذخیره
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
