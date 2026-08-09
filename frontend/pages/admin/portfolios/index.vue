<script setup lang="ts">
import { Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { AdminPortfolio } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const { data: portfolios, refresh } = await useAsyncData('admin-portfolios', () =>
  apiFetch<AdminPortfolio[]>('/admin/portfolios'),
)

function groups(pf: AdminPortfolio): any[] {
  const g = (pf.content as any)?.groups
  return Array.isArray(g) ? g : []
}
function productCount(pf: AdminPortfolio): number {
  return groups(pf).reduce(
    (n, g) => n + (Array.isArray(g?.product_ids) ? g.product_ids.length : 0),
    0,
  )
}

// --- Create ---
const createOpen = ref(false)
const createForm = reactive({ name: '', slug: '' })
const createError = ref('')
const creating = ref(false)

async function createPortfolio() {
  createError.value = ''
  if (!createForm.name.trim() || !createForm.slug.trim()) {
    createError.value = 'نام و اسلاگ لازم است.'
    return
  }
  creating.value = true
  try {
    const pf = await apiFetch<AdminPortfolio>('/admin/portfolios', {
      method: 'POST',
      body: { name: createForm.name.trim(), slug: createForm.slug.trim() },
    })
    createOpen.value = false
    createForm.name = ''
    createForm.slug = ''
    await navigateTo(`/admin/portfolios/${pf.id}`)
  } catch (e: any) {
    createError.value =
      e?.data?.detail || 'ساخت پورتفولیو ناموفق بود (اسلاگ باید انگلیسی و یکتا باشد).'
  } finally {
    creating.value = false
  }
}

async function remove(pf: AdminPortfolio) {
  if (!confirm(`پورتفولیو «${pf.name}» حذف شود؟`)) return
  await apiFetch(`/admin/portfolios/${pf.id}`, { method: 'DELETE' })
  await refresh()
}
</script>

<template>
  <div>
    <AdminPageHeader
      title="پورتفولیوها"
      subtitle="مجموعه‌های محصول بسازید و آن‌ها را به‌صورت بخش‌های ویژه در بالای فروشگاه نمایش دهید."
    >
      <button
        class="flex h-11 shrink-0 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        @click="createOpen = true"
      >
        <Plus :size="16" /> پورتفولیوی جدید
      </button>
    </AdminPageHeader>

    <ul class="space-y-3">
      <li
        v-for="pf in portfolios"
        :key="pf.id"
        class="admin-card admin-card--hover flex items-center gap-4 p-4"
      >
        <div class="min-w-0 flex-1">
          <p class="flex items-center gap-2 text-ink">
            {{ pf.name }}
            <span
              v-if="!pf.is_active"
              class="border border-line px-1.5 py-0.5 text-[11px] text-ink-muted"
            >غیرفعال</span>
          </p>
          <p class="tnum text-xs text-ink-muted" dir="ltr">
            {{ pf.slug }} · {{ toFa(groups(pf).length) }} گروه · {{ toFa(productCount(pf)) }} محصول
          </p>
        </div>
        <NuxtLink
          :to="`/admin/portfolios/${pf.id}`"
          class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        >
          <Pencil :size="16" /> ویرایش
        </NuxtLink>
        <button
          class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger"
          aria-label="حذف پورتفولیو"
          @click="remove(pf)"
        >
          <Trash2 :size="16" />
        </button>
      </li>
    </ul>
    <p v-if="portfolios && !portfolios.length" class="admin-card py-12 text-center text-sm text-ink-muted">
      هنوز پورتفولیویی نساخته‌اید.
    </p>

    <BaseSheet v-model="createOpen" title="پورتفولیوی جدید">
      <div class="space-y-5">
        <FormField label="نام" v-slot="{ id }">
          <input :id="id" v-model="createForm.name" class="form-control" placeholder="مثلاً کالکشن عید" />
        </FormField>
        <FormField label="اسلاگ (انگلیسی، شناسه یکتا)" v-slot="{ id }">
          <input :id="id" v-model="createForm.slug" dir="ltr" class="form-control" placeholder="eid-collection" />
        </FormField>
        <p v-if="createError" class="text-sm text-danger">{{ createError }}</p>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="creating"
          @click="createPortfolio"
        >
          {{ creating ? 'در حال ساخت…' : 'ساخت و ویرایش' }}
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
