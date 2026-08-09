<script setup lang="ts">
import { PackagePlus, Undo2 } from 'lucide-vue-next'
import { computed, reactive, ref, watch } from 'vue'
import type { GalleryResponse } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const KIND_LABEL = { sample: 'نمونه', sellable: 'قابل فروش' } as const
const STATUS_LABEL = { with_agent: 'همراه ایجنت', returned: 'برگشتی', sold: 'فروخته‌شده' } as const
const STATUS_CLASS = {
  with_agent: 'bg-warning-soft text-warning',
  returned: 'bg-surface-soft text-ink-muted',
  sold: 'bg-success-soft text-success',
} as const

interface AgentRow { id: string; username: string; full_name: string | null }
const { data: agents } = await useAsyncData('gallery-agents', () =>
  apiFetch<AgentRow[]>('/admin/mobile-gallery/agents'),
)
const agentId = ref('')
watch(agents, (a) => { if (a?.length && !agentId.value) agentId.value = a[0].id }, { immediate: true })

const { data, refresh } = await useAsyncData(
  'admin-mobile-gallery',
  () => (agentId.value ? apiFetch<GalleryResponse>(`/admin/mobile-gallery?agent_id=${agentId.value}`) : Promise.resolve(null)),
  { watch: [agentId] },
)

const chips = computed(() => {
  const c = data.value?.counts
  if (!c) return []
  return [
    { label: 'همراه ایجنت', v: c.with_agent },
    { label: 'نمونه', v: c.sample },
    { label: 'قابل فروش', v: c.sellable },
    { label: 'فروخته‌شده', v: c.sold },
    { label: 'برگشتی', v: c.returned },
  ]
})

// --- Assign form ---
const assign = reactive({ code: '', kind: '' as '' | 'sample' | 'sellable', note: '' })
const assigning = ref(false)
const assignError = ref('')
const { toast } = useToast()

async function doAssign() {
  assigning.value = true
  assignError.value = ''
  try {
    await apiFetch('/admin/mobile-gallery', {
      method: 'POST',
      body: {
        agent_id: agentId.value,
        code: assign.code,
        kind: assign.kind || null,
        note: assign.note || null,
      },
    })
    toast('قطعه تحویل ایجنت شد')
    assign.code = ''
    assign.note = ''
    await refresh()
  } catch (e: any) {
    assignError.value = e?.data?.detail || 'ثبت ناموفق بود.'
  } finally {
    assigning.value = false
  }
}

async function doReturn(itemId: string) {
  await apiFetch(`/admin/mobile-gallery/${itemId}/return`, { method: 'PATCH' })
  toast('برگشت ثبت شد')
  await refresh()
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <AdminPageHeader title="گالری سیار" subtitle="کالاهایی که هر ایجنت برای نمایش یا فروش همراه دارد." />

    <div class="mb-4 grid gap-3 sm:grid-cols-2">
      <select v-model="agentId" class="form-control h-11" aria-label="ایجنت">
        <option v-for="a in agents" :key="a.id" :value="a.id">
          {{ a.full_name || a.username }}
        </option>
      </select>
    </div>

    <p v-if="agents && !agents.length" class="admin-card p-6 text-center text-sm text-ink-muted">
      هنوز ایجنتی تعریف نشده است (مدیریت سیستم ← کاربران).
    </p>

    <template v-else>
      <!-- Stock report chips -->
      <div v-if="chips.length" class="mb-4 flex flex-wrap gap-2">
        <span v-for="c in chips" :key="c.label" class="corner-soft border border-line bg-surface-raised px-3 py-1.5 text-sm">
          {{ c.label }}: <span class="tnum font-medium text-gold-text">{{ toFa(c.v) }}</span>
        </span>
      </div>

      <!-- Assign (initial hand-off) -->
      <div class="admin-card mb-6">
        <h2 class="mb-3 flex items-center gap-2 text-base font-medium">
          <PackagePlus :size="18" class="text-gold-text" /> تحویل قطعه به ایجنت
        </h2>
        <div class="grid gap-3 sm:grid-cols-[1fr_10rem_1fr_auto]">
          <input v-model="assign.code" dir="ltr" placeholder="DGV-XXXXXXXX" class="form-control h-11" aria-label="کد سریال" />
          <select v-model="assign.kind" class="form-control h-11" aria-label="نوع">
            <option value="">نوع: خودکار</option>
            <option value="sellable">قابل فروش</option>
            <option value="sample">نمونه</option>
          </select>
          <input v-model="assign.note" placeholder="یادداشت (اختیاری)" class="form-control h-11" />
          <button
            class="h-11 bg-navy px-5 text-sm text-white hover:bg-gold disabled:opacity-60"
            :disabled="assigning || !assign.code || !agentId"
            @click="doAssign"
          >
            {{ assigning ? '…' : 'تحویل' }}
          </button>
        </div>
        <p v-if="assignError" class="mt-2 text-sm text-danger">{{ assignError }}</p>
      </div>

      <!-- Items -->
      <div class="admin-card overflow-x-auto p-0">
        <table class="w-full text-start text-sm">
          <thead class="bg-surface-soft text-ink-muted">
            <tr>
              <th class="p-3 text-start">کد قطعه</th>
              <th class="p-3 text-start">محصول</th>
              <th class="p-3 text-start">نوع</th>
              <th class="p-3 text-start">وضعیت</th>
              <th class="p-3 text-start">تاریخ تحویل</th>
              <th class="p-3 text-start"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in data?.items" :key="i.id" class="border-t border-line hover:bg-surface-soft">
              <td class="tnum p-3 font-medium text-gold-text" dir="ltr">{{ i.code }}</td>
              <td class="p-3">{{ i.product_name }}</td>
              <td class="p-3">{{ KIND_LABEL[i.kind] }}</td>
              <td class="p-3">
                <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[i.status]">{{ STATUS_LABEL[i.status] }}</span>
              </td>
              <td class="tnum p-3 text-ink-muted">{{ faDate(i.created_at) }}</td>
              <td class="p-3 text-end">
                <button
                  v-if="i.status === 'with_agent'"
                  class="inline-flex items-center gap-1 border border-line px-3 py-1.5 text-xs hover:border-gold"
                  @click="doReturn(i.id)"
                >
                  <Undo2 :size="13" /> ثبت برگشت
                </button>
              </td>
            </tr>
            <tr v-if="!data?.items?.length">
              <td colspan="6" class="p-10 text-center text-ink-muted">قطعه‌ای برای این ایجنت ثبت نشده است.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
