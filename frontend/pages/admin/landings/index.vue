<script setup lang="ts">
import { ExternalLink, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { AdminLanding } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const { data: landings, refresh } = await useAsyncData('admin-landings', () =>
  apiFetch<AdminLanding[]>('/admin/landings'),
)

function groups(ln: AdminLanding): any[] {
  const g = (ln.content as any)?.groups
  return Array.isArray(g) ? g : []
}
function productCount(ln: AdminLanding): number {
  return groups(ln).reduce(
    (n, g) => n + (Array.isArray(g?.product_ids) ? g.product_ids.length : 0),
    0,
  )
}

// --- Create ---
const createOpen = ref(false)
const createForm = reactive({ slug: '', title: '' })
const createError = ref('')
const creating = ref(false)

async function createLanding() {
  createError.value = ''
  if (!createForm.slug.trim() || !createForm.title.trim()) {
    createError.value = 'اسلاگ و عنوان لازم است.'
    return
  }
  creating.value = true
  try {
    const ln = await apiFetch<AdminLanding>('/admin/landings', {
      method: 'POST',
      body: { slug: createForm.slug.trim(), title: createForm.title.trim() },
    })
    createOpen.value = false
    createForm.slug = ''
    createForm.title = ''
    await navigateTo(`/admin/landings/${ln.id}`)
  } catch (e: any) {
    createError.value =
      e?.data?.detail || 'ساخت صفحه ناموفق بود (اسلاگ باید انگلیسی و یکتا باشد).'
  } finally {
    creating.value = false
  }
}

async function remove(ln: AdminLanding) {
  if (!confirm(`صفحه فرود «${ln.title}» و همه محتوای آن حذف شود؟`)) return
  await apiFetch(`/admin/landings/${ln.id}`, { method: 'DELETE' })
  await refresh()
}
</script>

<template>
  <div>
    <AdminPageHeader
      title="صفحات فرود"
      subtitle="صفحه فرود بسازید و محتوای هر بخش (هیرو، اعتماد، محصولات، سؤالات، فوتر) را جداگانه ویرایش کنید."
    >
      <button
        class="flex h-11 shrink-0 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        @click="createOpen = true"
      >
        <Plus :size="16" /> صفحه جدید
      </button>
    </AdminPageHeader>

    <ul class="space-y-3">
      <li
        v-for="ln in landings"
        :key="ln.id"
        class="admin-card admin-card--hover flex items-center gap-4 p-4"
      >
        <div class="min-w-0 flex-1">
          <p class="text-ink">{{ ln.title }}</p>
          <p class="tnum text-xs text-ink-muted" dir="ltr">
            /l/{{ ln.slug }} · {{ toFa(groups(ln).length) }} گروه · {{ toFa(productCount(ln)) }} محصول
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
        <NuxtLink
          :to="`/admin/landings/${ln.id}`"
          class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        >
          <Pencil :size="16" /> ویرایش
        </NuxtLink>
        <button
          class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger"
          aria-label="حذف صفحه"
          @click="remove(ln)"
        >
          <Trash2 :size="16" />
        </button>
      </li>
    </ul>

    <BaseSheet v-model="createOpen" title="صفحه فرود جدید">
      <div class="space-y-5">
        <FormField label="عنوان" v-slot="{ id }">
          <input :id="id" v-model="createForm.title" class="form-control" placeholder="مثلاً کالکشن عروس" />
        </FormField>
        <FormField label="اسلاگ (انگلیسی، در آدرس /l/… نمایش داده می‌شود)" v-slot="{ id }">
          <input
            :id="id"
            v-model="createForm.slug"
            dir="ltr"
            class="form-control"
            placeholder="wedding"
          />
        </FormField>
        <p v-if="createError" class="text-sm text-danger">{{ createError }}</p>
        <p class="text-xs text-ink-muted">
          صفحه با یک ساختار استاندارد و محتوای پیش‌فرض ساخته می‌شود؛ سپس هر بخش را ویرایش می‌کنید.
        </p>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="creating"
          @click="createLanding"
        >
          {{ creating ? 'در حال ساخت…' : 'ساخت و ویرایش' }}
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
