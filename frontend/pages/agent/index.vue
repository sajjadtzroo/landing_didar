<script setup lang="ts">
import { MapPin, NotebookPen, Phone, ShoppingCart } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { AgentRetailer, AgentVisit } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'agent', middleware: 'agent' })

const { data: retailers } = await useAsyncData('agent-retailers', () =>
  apiFetch<AgentRetailer[]>('/agent/retailers'),
)

// --- Visit note sheet ---
const visitOpen = ref(false)
const visit = reactive({ customer_id: '', store: '', note: '' })
const visits = ref<AgentVisit[]>([])
const savingVisit = ref(false)
const { toast } = useToast()

async function startVisit(r: AgentRetailer) {
  visit.customer_id = r.id
  visit.store = r.store_name || r.full_name || r.phone
  visit.note = ''
  visitOpen.value = true
  visits.value = await apiFetch<AgentVisit[]>(`/agent/visits?customer_id=${r.id}`)
}
async function saveVisit() {
  savingVisit.value = true
  try {
    await apiFetch('/agent/visits', {
      method: 'POST',
      body: { customer_id: visit.customer_id, note: visit.note },
    })
    toast('بازدید ثبت شد')
    visitOpen.value = false
  } finally {
    savingVisit.value = false
  }
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <h1 class="mb-1 text-xl font-medium">کاسبان من</h1>
    <p class="mb-5 text-sm text-ink-muted">خرده‌فروشان تخصیص‌یافته به شما؛ ثبت سفارش و بازدید.</p>

    <div class="space-y-3">
      <div
        v-for="r in retailers"
        :key="r.id"
        class="corner-soft border border-line bg-surface-raised p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="font-medium text-ink">{{ r.store_name || r.full_name || '—' }}</p>
            <p v-if="r.full_name && r.store_name" class="mt-0.5 text-sm text-ink-muted">{{ r.full_name }}</p>
            <p v-if="r.province" class="mt-1 flex items-center gap-1 text-xs text-ink-muted">
              <MapPin :size="12" /> {{ r.province }}<template v-if="r.city">، {{ r.city }}</template>
            </p>
          </div>
          <a
            :href="`tel:${r.phone}`"
            class="flex h-10 w-10 shrink-0 items-center justify-center border border-line text-ink-muted hover:border-gold hover:text-gold-text"
            :aria-label="`تماس با ${r.store_name}`"
          >
            <Phone :size="16" />
          </a>
        </div>
        <div class="mt-3 flex gap-2">
          <NuxtLink
            :to="`/agent/order/${r.id}`"
            class="flex h-11 flex-1 items-center justify-center gap-2 bg-navy text-sm font-medium text-white hover:bg-gold"
          >
            <ShoppingCart :size="16" /> ثبت سفارش
          </NuxtLink>
          <button
            type="button"
            class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold"
            @click="startVisit(r)"
          >
            <NotebookPen :size="16" /> بازدید
          </button>
        </div>
      </div>
    </div>

    <p v-if="retailers && !retailers.length" class="corner-soft border border-line bg-surface-raised py-12 text-center text-sm text-ink-muted">
      هنوز خرده‌فروشی به شما تخصیص داده نشده است.
    </p>

    <!-- Visit note sheet -->
    <BaseSheet v-model="visitOpen" :title="`بازدید — ${visit.store}`">
      <div class="space-y-4">
        <FormField label="یادداشت بازدید" v-slot="{ id }">
          <textarea :id="id" v-model="visit.note" rows="3" maxlength="500" class="form-control h-auto py-3" />
        </FormField>
        <div v-if="visits.length">
          <p class="mb-2 text-xs text-ink-muted">بازدیدهای قبلی</p>
          <ul class="space-y-2">
            <li v-for="v in visits" :key="v.id" class="border border-line bg-surface p-3 text-sm">
              <p>{{ v.note }}</p>
              <p class="tnum mt-1 text-xs text-ink-muted">{{ faDate(v.created_at) }}</p>
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="savingVisit || visit.note.trim().length < 2"
          @click="saveVisit"
        >
          {{ savingVisit ? 'در حال ثبت…' : 'ثبت بازدید' }}
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
