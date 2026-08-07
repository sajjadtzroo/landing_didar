<script setup lang="ts">
import { MessageSquare, Phone } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { CONTENT } from '~/constants/content'
import { STATUS_FLOW, STATUS_LABEL } from '~/constants/orderStatus'
import type { AdminOrderDetail, OrderStatus } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const id = route.params.id as string

const { data: order, refresh } = await useAsyncData(`order-${id}`, () =>
  apiFetch<AdminOrderDetail>(`/admin/orders/${id}`),
)

const note = ref(order.value?.internal_note ?? '')
const saving = ref(false)

// Mark unread orders read on open.
watch(
  order,
  async (o) => {
    if (o && !o.is_read) {
      await apiFetch(`/admin/orders/${id}`, { method: 'PATCH', body: { is_read: true } })
    }
  },
  { immediate: true },
)

async function setStatus(status: OrderStatus) {
  await apiFetch(`/admin/orders/${id}`, { method: 'PATCH', body: { status } })
  await refresh()
}

async function saveNote() {
  saving.value = true
  try {
    await apiFetch(`/admin/orders/${id}`, {
      method: 'PATCH',
      body: { internal_note: note.value },
    })
    await refresh()
  } finally {
    saving.value = false
  }
}

function faDateTime(iso: string) {
  return toFa(new Date(iso).toLocaleString('en-GB'))
}
</script>

<template>
  <div v-if="order">
    <NuxtLink to="/admin/orders" class="text-sm text-ink-muted hover:text-ink">‹ بازگشت</NuxtLink>

    <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-medium">
        سفارش <span class="tnum" dir="ltr">{{ order.reference }}</span>
      </h1>
      <div class="flex gap-2">
        <a
          :href="`tel:${order.phone}`"
          class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        >
          <Phone :size="16" /> تماس
        </a>
        <a
          :href="`sms:${order.phone}`"
          class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold"
        >
          <MessageSquare :size="16" /> پیامک
        </a>
      </div>
    </div>

    <div class="mt-6 grid gap-6 md:grid-cols-2">
      <!-- Customer -->
      <section class="border border-line bg-surface-raised p-5">
        <h2 class="mb-4 text-lg font-medium">اطلاعات مشتری</h2>
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between"><dt class="text-ink-muted">نام</dt><dd>{{ order.full_name }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">موبایل</dt><dd class="tnum" dir="ltr">{{ order.phone }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">فروشگاه</dt><dd>{{ order.store_name }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">استان</dt><dd>{{ order.province }}</dd></div>
          <div v-if="order.city" class="flex justify-between"><dt class="text-ink-muted">شهر</dt><dd>{{ order.city }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">روش پیگیری</dt><dd>{{ CONTENT.form.contactMethods[order.contact_method] }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">تاریخ</dt><dd class="tnum">{{ faDateTime(order.created_at) }}</dd></div>
          <div v-if="order.utm_source" class="flex justify-between"><dt class="text-ink-muted">منبع</dt><dd>{{ order.utm_source }}</dd></div>
        </dl>
      </section>

      <!-- Status + note -->
      <section class="border border-line bg-surface-raised p-5">
        <h2 class="mb-4 text-lg font-medium">وضعیت</h2>
        <select
          :value="order.status"
          class="form-control"
          @change="setStatus(($event.target as HTMLSelectElement).value as OrderStatus)"
        >
          <option v-for="s in STATUS_FLOW" :key="s" :value="s">{{ STATUS_LABEL[s] }}</option>
        </select>

        <h3 class="mb-2 mt-5 text-sm text-ink-muted">یادداشت داخلی</h3>
        <textarea v-model="note" rows="3" maxlength="300" class="form-control h-auto py-3" />
        <button
          class="mt-2 h-11 bg-navy px-5 text-sm text-white hover:bg-gold disabled:opacity-60"
          :disabled="saving"
          @click="saveNote"
        >
          ذخیره یادداشت
        </button>

        <h3 class="mb-2 mt-5 text-sm text-ink-muted">تاریخچه وضعیت</h3>
        <ul class="space-y-1 text-xs text-ink-muted">
          <li v-for="(log, i) in order.status_log" :key="i" class="tnum">
            {{ faDateTime(log.created_at) }} —
            {{ log.from_status ? STATUS_LABEL[log.from_status] + ' ← ' : '' }}
            {{ STATUS_LABEL[log.to_status] }}
          </li>
        </ul>
      </section>
    </div>

    <!-- Line items -->
    <section class="mt-6 border border-line bg-surface-raised p-5">
      <h2 class="mb-4 text-lg font-medium">اقلام سفارش</h2>
      <ul class="divide-y divide-line">
        <li v-for="(it, i) in order.items" :key="i" class="flex justify-between py-3 text-sm">
          <span>{{ it.product_name }} × {{ toFa(it.quantity) }}</span>
          <span class="tnum text-gold-text">{{ formatPrice(it.unit_price) ?? 'استعلام' }}</span>
        </li>
      </ul>
      <div class="mt-4 flex justify-between border-t border-line pt-3 font-medium">
        <span>جمع کل</span>
        <span class="tnum text-gold-text">{{ formatPrice(order.total) ?? '—' }}</span>
      </div>
      <p v-if="order.note" class="mt-4 border-t border-line pt-3 text-sm text-ink-muted">
        توضیحات مشتری: {{ order.note }}
      </p>
    </section>
  </div>
</template>
