<script setup lang="ts">
import { ArrowRight, Minus, Plus } from 'lucide-vue-next'
import { computed, reactive, ref } from 'vue'
import { PROVINCES } from '~/constants/provinces'
import type { AgentRetailer, Product } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'agent', middleware: 'agent' })

const route = useRoute()
const customerId = route.params.customer as string

const { data: retailers } = await useAsyncData('agent-retailers', () =>
  apiFetch<AgentRetailer[]>('/agent/retailers'),
)
const retailer = computed(() => retailers.value?.find((r) => r.id === customerId))

const { data: products } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})
const orderable = computed(() =>
  (products.value || []).filter((p) => p.product_status !== 'sample'),
)

// customer_id → quantity
const qty = reactive<Record<string, number>>({})
function inc(id: string) {
  qty[id] = (qty[id] || 0) + 1
}
function dec(id: string) {
  if (qty[id]) qty[id] = Math.max(0, qty[id] - 1)
}
const items = computed(() =>
  Object.entries(qty)
    .filter(([, q]) => q > 0)
    .map(([product_id, quantity]) => ({ product_id, quantity })),
)
const totalGrams = computed(() =>
  Object.entries(qty).reduce((sum, [id, q]) => {
    const p = orderable.value.find((x) => x.id === id)
    return sum + (p?.weight_grams ? Number(p.weight_grams) * q : 0)
  }, 0),
)

const province = ref('')
const note = ref('')
if (retailer.value?.province) province.value = retailer.value.province

const submitting = ref(false)
const error = ref('')
async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const order = await apiFetch<{ reference: string }>('/agent/orders', {
      method: 'POST',
      body: {
        customer_id: customerId,
        province: province.value,
        note: note.value || null,
        items: items.value,
      },
    })
    await navigateTo(`/agent/orders?created=${order.reference}`)
  } catch (e: any) {
    error.value = e?.data?.detail || 'ثبت سفارش ناموفق بود.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <NuxtLink to="/agent" class="mb-4 inline-flex items-center gap-1 text-sm text-ink-muted hover:text-ink">
      <ArrowRight :size="15" /> بازگشت
    </NuxtLink>
    <h1 class="mb-1 text-xl font-medium">
      سفارش برای {{ retailer?.store_name || retailer?.full_name || '…' }}
    </h1>
    <p class="mb-5 text-sm text-ink-muted">تعداد هر قطعه را مشخص کنید؛ وزن‌ها از کاتالوگ محاسبه می‌شود.</p>

    <!-- Product picker -->
    <div class="space-y-2">
      <div
        v-for="p in orderable"
        :key="p.id"
        class="flex items-center gap-3 border border-line bg-surface-raised p-3"
        :class="qty[p.id] ? 'border-gold' : ''"
      >
        <div class="h-12 w-12 shrink-0 overflow-hidden bg-media-surface">
          <NuxtImg v-if="p.image_url" :src="p.image_url" :alt="p.name" class="h-full w-full object-cover" width="48" height="48" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink">{{ p.name }}</p>
          <p class="tnum text-xs text-ink-muted">
            {{ p.sku }}<template v-if="p.weight_grams"> · {{ toFa(Number(p.weight_grams)) }} گرم</template>
          </p>
        </div>
        <div class="flex items-center border border-line">
          <button type="button" class="flex h-10 w-10 items-center justify-center text-ink hover:text-gold-text" aria-label="افزایش" @click="inc(p.id)">
            <Plus :size="16" />
          </button>
          <span class="tnum w-8 text-center text-sm">{{ toFa(qty[p.id] || 0) }}</span>
          <button type="button" class="flex h-10 w-10 items-center justify-center text-ink hover:text-gold-text disabled:opacity-30" :disabled="!qty[p.id]" aria-label="کاهش" @click="dec(p.id)">
            <Minus :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- Order meta + submit -->
    <div class="corner-soft mt-6 space-y-4 border border-line bg-surface-raised p-4">
      <FormField label="استان" v-slot="{ id }">
        <select :id="id" v-model="province" class="form-control">
          <option value="" disabled>انتخاب استان</option>
          <option v-for="p in PROVINCES" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
      </FormField>
      <FormField label="توضیحات (اختیاری)" v-slot="{ id }">
        <input :id="id" v-model="note" maxlength="300" class="form-control" />
      </FormField>
      <div class="flex items-center justify-between border-t border-line pt-3 text-sm">
        <span>جمع وزن</span>
        <span class="tnum font-medium text-gold-text">{{ toFa(totalGrams) }} گرم</span>
      </div>
      <p v-if="error" class="text-sm text-danger">{{ error }}</p>
      <button
        type="button"
        class="flex h-12 w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
        :disabled="submitting || !items.length || !province"
        @click="submit"
      >
        {{ submitting ? 'در حال ثبت…' : `ثبت سفارش (${toFa(items.length)} قلم)` }}
      </button>
    </div>
  </div>
</template>
