<script setup lang="ts">
import { CheckCircle2, PackageCheck } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import { STATUS_CLASS, STATUS_LABEL } from '~/constants/orderStatus'
import type { AdminOrder } from '~/types'
import { formatGrams, toFa } from '~/utils/format'

definePageMeta({ layout: 'agent', middleware: 'agent' })

const route = useRoute()
const created = ref(String(route.query.created || ''))

const { data: orders, refresh } = await useAsyncData('agent-orders', () =>
  apiFetch<AdminOrder[]>('/agent/orders'),
)

// --- Deliver with proof ---
const deliverOpen = ref(false)
const deliver = reactive({ id: '', reference: '', code: '', note: '' })
const delivering = ref(false)
const { toast } = useToast()

function startDeliver(o: AdminOrder) {
  deliver.id = o.id
  deliver.reference = o.reference
  deliver.code = ''
  deliver.note = ''
  deliverOpen.value = true
}
async function confirmDeliver() {
  delivering.value = true
  try {
    await apiFetch(`/agent/orders/${deliver.id}/deliver`, {
      method: 'POST',
      body: { code: deliver.code || null, note: deliver.note || null },
    })
    toast('تحویل ثبت شد؛ کدهای اصالت ساخته شدند')
    deliverOpen.value = false
    await refresh()
  } finally {
    delivering.value = false
  }
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <h1 class="mb-1 text-xl font-medium">سفارش‌های من</h1>
    <p class="mb-5 text-sm text-ink-muted">سفارش‌هایی که از طرف کاسبان ثبت کرده‌اید.</p>

    <p
      v-if="created"
      class="corner-soft mb-4 flex items-center gap-2 border border-line bg-success-soft p-3 text-sm text-success"
    >
      <CheckCircle2 :size="18" /> سفارش <span class="tnum" dir="ltr">{{ created }}</span> ثبت شد.
    </p>

    <div class="space-y-3">
      <div v-for="o in orders" :key="o.id" class="corner-soft border border-line bg-surface-raised p-4">
        <div class="flex items-center justify-between gap-2">
          <span class="tnum font-medium text-gold-text" dir="ltr">{{ o.reference }}</span>
          <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[o.status]">{{ STATUS_LABEL[o.status] }}</span>
        </div>
        <div class="mt-2 flex items-center justify-between text-sm">
          <span>{{ o.store_name }}</span>
          <span class="tnum text-gold-text">{{ formatGrams(o.total) ?? '—' }}</span>
        </div>
        <div class="mt-1 flex items-center justify-between text-xs text-ink-muted">
          <span class="tnum">{{ faDate(o.created_at) }}</span>
          <button
            v-if="o.status !== 'delivered' && o.status !== 'cancelled'"
            type="button"
            class="flex h-9 items-center gap-1.5 border border-line px-3 text-xs text-ink hover:border-gold"
            @click="startDeliver(o)"
          >
            <PackageCheck :size="14" /> ثبت تحویل
          </button>
        </div>
      </div>
    </div>

    <p v-if="orders && !orders.length" class="corner-soft border border-line bg-surface-raised py-12 text-center text-sm text-ink-muted">
      هنوز سفارشی ثبت نکرده‌اید.
    </p>

    <!-- Deliver sheet -->
    <BaseSheet v-model="deliverOpen" :title="`ثبت تحویل — ${deliver.reference}`">
      <div class="space-y-4">
        <FormField label="کد تأیید (اختیاری)" v-slot="{ id }">
          <input :id="id" v-model="deliver.code" dir="ltr" class="form-control" />
        </FormField>
        <FormField label="یادداشت تحویل (اختیاری)" v-slot="{ id }">
          <input :id="id" v-model="deliver.note" maxlength="300" class="form-control" />
        </FormField>
        <p class="text-xs text-ink-muted">
          با ثبت تحویل، وضعیت سفارش «تحویل‌شده» می‌شود و برای هر قطعه کد اصالت ساخته می‌شود.
        </p>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="delivering"
          @click="confirmDeliver"
        >
          {{ delivering ? 'در حال ثبت…' : 'ثبت تحویل' }}
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
