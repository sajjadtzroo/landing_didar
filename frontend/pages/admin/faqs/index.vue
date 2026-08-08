<script setup lang="ts">
import { ArrowDown, ArrowUp, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { FAQ } from '~/types'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const { data: faqs, refresh } = await useAsyncData('admin-faqs', () =>
  apiFetch<FAQ[]>('/admin/faqs'),
)

const blank = () => ({ id: '', question: '', answer: '', is_active: true })
const form = reactive(blank())
const editing = ref(false)
const panelOpen = ref(false)

function startCreate() {
  Object.assign(form, blank())
  editing.value = false
  panelOpen.value = true
}
function startEdit(f: FAQ) {
  Object.assign(form, { id: f.id, question: f.question, answer: f.answer, is_active: f.is_active })
  editing.value = true
  panelOpen.value = true
}

async function save() {
  const body = {
    question: form.question,
    answer: form.answer,
    is_active: form.is_active,
    sort_order: editing.value ? undefined : (faqs.value?.length ?? 0),
  }
  if (editing.value) await apiFetch(`/admin/faqs/${form.id}`, { method: 'PATCH', body })
  else await apiFetch('/admin/faqs', { method: 'POST', body })
  panelOpen.value = false
  await refresh()
}

async function remove(f: FAQ) {
  if (!confirm('حذف این سؤال؟')) return
  await apiFetch(`/admin/faqs/${f.id}`, { method: 'DELETE' })
  await refresh()
}

async function move(index: number, dir: -1 | 1) {
  const list = faqs.value
  if (!list) return
  const other = index + dir
  if (other < 0 || other >= list.length) return
  const a = list[index]
  const b = list[other]
  await Promise.all([
    apiFetch(`/admin/faqs/${a.id}`, { method: 'PATCH', body: { sort_order: b.sort_order } }),
    apiFetch(`/admin/faqs/${b.id}`, { method: 'PATCH', body: { sort_order: a.sort_order } }),
  ])
  await refresh()
}
</script>

<template>
  <div>
    <AdminPageHeader title="سؤالات متداول">
      <button class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold" @click="startCreate">
        <Plus :size="16" /> سؤال جدید
      </button>
    </AdminPageHeader>

    <ul class="space-y-3">
      <li v-for="(f, i) in faqs" :key="f.id" class="flex items-start gap-3 border border-line bg-surface-raised p-4" :class="!f.is_active ? 'opacity-60' : ''">
        <div class="flex flex-col">
          <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="i === 0" aria-label="بالا" @click="move(i, -1)"><ArrowUp :size="16" /></button>
          <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="i === (faqs?.length ?? 0) - 1" aria-label="پایین" @click="move(i, 1)"><ArrowDown :size="16" /></button>
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-ink">{{ f.question }}</p>
          <p class="mt-1 text-sm text-ink-muted">{{ f.answer }}</p>
        </div>
        <button class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-gold-text" aria-label="ویرایش" @click="startEdit(f)"><Pencil :size="16" /></button>
        <button class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger" aria-label="حذف" @click="remove(f)"><Trash2 :size="16" /></button>
      </li>
    </ul>

    <BaseSheet v-model="panelOpen" :title="editing ? 'ویرایش سؤال' : 'سؤال جدید'">
      <div class="space-y-4">
        <FormField label="سؤال" v-slot="{ id }"><input :id="id" v-model="form.question" class="form-control" /></FormField>
        <FormField label="پاسخ" v-slot="{ id }"><textarea :id="id" v-model="form.answer" rows="4" class="form-control h-auto py-3" /></FormField>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox" /> فعال</label>
      </div>
      <template #footer>
        <button class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold" @click="save">ذخیره</button>
      </template>
    </BaseSheet>
  </div>
</template>
