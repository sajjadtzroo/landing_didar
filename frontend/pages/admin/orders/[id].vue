<script setup lang="ts">
import { BadgeCheck, MessageSquare, Phone, Truck, Upload } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { CONTENT } from '~/constants/content'
import { STATUS_FLOW, STATUS_LABEL } from '~/constants/orderStatus'
import type { AdminOrderDetail, OrderStatus } from '~/types'
import { formatGrams, toFa } from '~/utils/format'

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

// --- Proof of Delivery (WO 7.7) ---
const { upload } = useAdminUpload()
const mediaUrl = useMediaUrl()
const assignee = ref(order.value?.delivery_assignee ?? '')
const proofCode = ref(order.value?.delivery_proof?.code ?? '')
const proofNote = ref(order.value?.delivery_proof?.note ?? '')
const proofPhoto = ref(order.value?.delivery_proof?.photo_url ?? '')
const uploadingProof = ref(false)
const savingProof = ref(false)

async function pickProofPhoto(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploadingProof.value = true
  try {
    proofPhoto.value = await upload(file)
  } finally {
    uploadingProof.value = false
    ;(e.target as HTMLInputElement).value = ''
  }
}

async function saveProof() {
  savingProof.value = true
  try {
    await apiFetch(`/admin/orders/${id}`, {
      method: 'PATCH',
      body: {
        delivery_assignee: assignee.value,
        delivery_proof: {
          photo_url: proofPhoto.value || null,
          code: proofCode.value || null,
          note: proofNote.value || null,
        },
      },
    })
    await refresh()
  } finally {
    savingProof.value = false
  }
}

const minting = ref(false)
async function genSerials() {
  minting.value = true
  try {
    await apiFetch(`/admin/orders/${id}/generate-serials`, { method: 'POST' })
    await refresh()
  } finally {
    minting.value = false
  }
}
function copyCode(c: string) {
  navigator.clipboard?.writeText(c)
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
      <section class="admin-card">
        <h2 class="mb-4 text-lg font-medium">اطلاعات مشتری</h2>
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between"><dt class="text-ink-muted">نام</dt><dd>{{ order.full_name }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">موبایل</dt><dd class="tnum" dir="ltr">{{ order.phone }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">فروشگاه</dt><dd>{{ order.store_name }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">استان</dt><dd>{{ order.province }}</dd></div>
          <div v-if="order.city" class="flex justify-between"><dt class="text-ink-muted">شهر</dt><dd>{{ order.city }}</dd></div>
          <div class="flex justify-between"><dt class="text-ink-muted">روش پیگیری</dt><dd>{{ CONTENT.form.contactMethods[order.contact_method] }}</dd></div>
          <div v-if="order.agent_username" class="flex justify-between">
            <dt class="text-ink-muted">ثبت توسط ایجنت</dt>
            <dd class="tnum" dir="ltr">{{ order.agent_username }}</dd>
          </div>
          <div class="flex justify-between"><dt class="text-ink-muted">تاریخ</dt><dd class="tnum">{{ faDateTime(order.created_at) }}</dd></div>
          <div v-if="order.utm_source" class="flex justify-between"><dt class="text-ink-muted">منبع</dt><dd>{{ order.utm_source }}</dd></div>
        </dl>
      </section>

      <!-- Status + note -->
      <section class="admin-card">
        <h2 class="mb-4 text-lg font-medium">وضعیت</h2>
        <select
          :value="order.status"
          class="form-control"
          aria-label="وضعیت سفارش"
          @change="setStatus(($event.target as HTMLSelectElement).value as OrderStatus)"
        >
          <option v-for="s in STATUS_FLOW" :key="s" :value="s">{{ STATUS_LABEL[s] }}</option>
        </select>

        <label for="order-note" class="mb-2 mt-5 block text-sm text-ink-muted">یادداشت داخلی</label>
        <textarea id="order-note" v-model="note" rows="3" maxlength="300" class="form-control h-auto py-3" />
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
    <section class="admin-card mt-6">
      <h2 class="mb-4 text-lg font-medium">اقلام سفارش</h2>
      <ul class="divide-y divide-line">
        <li v-for="(it, i) in order.items" :key="i" class="flex justify-between py-3 text-sm">
          <span>{{ it.product_name }} × {{ toFa(it.quantity) }}</span>
          <span class="tnum text-gold-text">{{ formatGrams(it.unit_weight_grams) ?? '—' }}</span>
        </li>
      </ul>
      <div class="mt-4 flex justify-between border-t border-line pt-3 font-medium">
        <span>وزن کل</span>
        <span class="tnum text-gold-text">{{ formatGrams(order.total) ?? '—' }}</span>
      </div>
      <p v-if="order.note" class="mt-4 border-t border-line pt-3 text-sm text-ink-muted">
        توضیحات مشتری: {{ order.note }}
      </p>
    </section>

    <!-- Authenticity serials -->
    <section class="admin-card mt-6">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 text-lg font-medium">
          <BadgeCheck :size="18" class="text-gold-text" /> سریال‌های اصالت
        </h2>
        <button
          v-if="!order.serial_codes?.length"
          class="flex h-10 items-center gap-2 border border-line px-4 text-sm hover:border-gold disabled:opacity-60"
          :disabled="minting"
          @click="genSerials"
        >
          {{ minting ? 'در حال تولید…' : 'تولید سریال برای این سفارش' }}
        </button>
      </div>
      <ul v-if="order.serial_codes?.length" class="flex flex-wrap gap-2">
        <li v-for="c in order.serial_codes" :key="c">
          <button
            class="tnum inline-flex items-center gap-1.5 border border-line px-3 py-1.5 text-sm text-gold-text hover:border-gold"
            dir="ltr"
            title="کپی"
            @click="copyCode(c)"
          >
            {{ c }}
          </button>
        </li>
      </ul>
      <p v-else class="text-sm text-ink-muted">
        با تحویل سفارش، برای هر قطعه یک کد اصالت ساخته می‌شود.
      </p>
    </section>

    <!-- Proof of Delivery (only once the order is delivered) -->
    <section v-if="order.status === 'delivered'" class="admin-card mt-6">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 text-lg font-medium">
          <Truck :size="18" class="text-gold-text" /> تحویل و رسید
        </h2>
        <span v-if="order.delivered_at" class="tnum text-xs text-ink-muted">
          تاریخ تحویل: {{ faDateTime(order.delivered_at) }}
        </span>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <FormField label="تحویل‌دهنده (ایجنت / پیک)" v-slot="{ id: fid }">
          <input :id="fid" v-model="assignee" class="form-control" />
        </FormField>
        <FormField label="کد تأیید (اختیاری)" v-slot="{ id: fid }">
          <input :id="fid" v-model="proofCode" dir="ltr" class="form-control" />
        </FormField>
      </div>

      <FormField label="یادداشت تحویل (اختیاری)" class="mt-4" v-slot="{ id: fid }">
        <input :id="fid" v-model="proofNote" class="form-control" />
      </FormField>

      <!-- Photo evidence (doubles as the signature for MVP) -->
      <div class="mt-4">
        <p class="mb-1.5 text-sm text-ink-muted">عکس رسید / تحویل</p>
        <label class="inline-flex cursor-pointer items-center gap-2 text-sm text-gold-text hover:underline">
          <Upload :size="15" />
          {{ uploadingProof ? 'در حال بارگذاری…' : proofPhoto ? 'تعویض عکس' : 'بارگذاری عکس' }}
          <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickProofPhoto" />
        </label>
        <a v-if="proofPhoto" :href="mediaUrl(proofPhoto)" target="_blank" rel="noopener" class="mt-2 block w-40">
          <img :src="mediaUrl(proofPhoto)" alt="رسید تحویل" class="corner-soft w-40 border border-line object-cover" />
        </a>
      </div>

      <button
        class="mt-5 h-11 bg-navy px-5 text-sm text-white hover:bg-gold disabled:opacity-60"
        :disabled="savingProof || uploadingProof"
        @click="saveProof"
      >
        {{ savingProof ? 'در حال ذخیره…' : 'ذخیره رسید تحویل' }}
      </button>
    </section>
  </div>
</template>
