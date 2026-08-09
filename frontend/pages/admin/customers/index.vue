<script setup lang="ts">
import { ShieldCheck, ShieldX } from 'lucide-vue-next'
import { reactive, ref, watch } from 'vue'
import type { CustomerAdmin } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

type VerificationStatus = 'unverified' | 'pending' | 'approved' | 'rejected' | ''

const STATUS_LABEL: Record<string, string> = {
  unverified: 'تأیید نشده',
  pending: 'در انتظار',
  approved: 'تأیید شده',
  rejected: 'رد شده',
}

const STATUS_CLASS: Record<string, string> = {
  unverified: 'bg-surface-soft text-ink-muted',
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-700',
}

const filters = reactive({
  status: 'pending' as VerificationStatus,
})

function query() {
  const p = new URLSearchParams()
  if (filters.status) p.set('status', filters.status)
  return p.toString()
}

const { data, refresh } = await useAsyncData(
  'admin-customers',
  () => apiFetch<CustomerAdmin[]>(`/admin/customers?${query()}`),
)

watch(() => filters.status, () => {
  refresh()
})

// Per-row state: which row is in reject-reason mode, and the reason text.
const rejectingId = ref<string | null>(null)
const rejectReason = ref('')
const busy = ref<string | null>(null)

function isImage(url: string) {
  return /\.(jpe?g|png|gif|webp|svg)(\?|$)/i.test(url)
}

async function verify(customer: CustomerAdmin, status: 'approved' | 'rejected', reason?: string) {
  busy.value = customer.id
  try {
    await apiFetch(`/admin/customers/${customer.id}/verification`, {
      method: 'PATCH',
      body: { status, ...(reason ? { reason } : {}) },
    })
    rejectingId.value = null
    rejectReason.value = ''
    await refresh()
  } finally {
    busy.value = null
  }
}

function startReject(id: string) {
  rejectingId.value = id
  rejectReason.value = ''
}

function cancelReject() {
  rejectingId.value = null
  rejectReason.value = ''
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <AdminPageHeader title="احراز هویت مشتریان" />

    <!-- Status filter -->
    <div class="mb-4">
      <select v-model="filters.status" class="form-control w-full sm:w-56">
        <option value="pending">در انتظار بررسی</option>
        <option value="approved">تأیید شده</option>
        <option value="rejected">رد شده</option>
        <option value="unverified">تأیید نشده</option>
        <option value="">همه</option>
      </select>
    </div>

    <!-- Desktop table -->
    <div class="admin-card hidden overflow-x-auto p-0 md:block">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">تاریخ</th>
            <th class="p-3 text-start">نام</th>
            <th class="p-3 text-start">موبایل</th>
            <th class="p-3 text-start">فروشگاه</th>
            <th class="p-3 text-start">وضعیت</th>
            <th class="p-3 text-start">مدارک</th>
            <th class="p-3 text-start">عملیات</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="c in data" :key="c.id">
            <tr class="border-t border-line hover:bg-surface-soft">
              <td class="tnum p-3">{{ faDate(c.created_at) }}</td>
              <td class="p-3">{{ c.full_name ?? '—' }}</td>
              <td class="tnum p-3" dir="ltr">{{ c.phone }}</td>
              <td class="p-3">{{ c.store_name ?? '—' }}</td>
              <td class="p-3">
                <span class="px-2 py-1 text-xs" :class="STATUS_CLASS[c.verification_status]">
                  {{ STATUS_LABEL[c.verification_status] }}
                </span>
              </td>
              <!-- Documents -->
              <td class="p-3">
                <div class="flex flex-wrap gap-2">
                  <template v-if="c.verification_documents.length">
                    <a
                      v-for="(doc, i) in c.verification_documents"
                      :key="i"
                      :href="doc.url"
                      target="_blank"
                      rel="noopener"
                      class="block"
                      :title="doc.filename ?? `سند ${toFa(i + 1)}`"
                    >
                      <img
                        v-if="isImage(doc.url)"
                        :src="doc.url"
                        :alt="doc.filename ?? `سند ${toFa(i + 1)}`"
                        class="h-14 w-14 rounded border border-line object-cover"
                      />
                      <span
                        v-else
                        class="flex h-14 w-24 items-center justify-center border border-line bg-surface-soft text-xs text-ink-muted hover:border-gold"
                      >
                        {{ doc.filename ?? `سند ${toFa(i + 1)}` }}
                      </span>
                    </a>
                  </template>
                  <span v-else class="text-ink-muted">—</span>
                </div>
              </td>
              <!-- Actions -->
              <td class="p-3">
                <div class="flex flex-wrap items-center gap-2">
                  <button
                    v-if="c.verification_status !== 'approved'"
                    class="flex h-9 items-center gap-1 bg-green-700 px-3 text-xs text-white hover:bg-green-800 disabled:opacity-50"
                    :disabled="busy === c.id"
                    @click="verify(c, 'approved')"
                  >
                    <ShieldCheck :size="14" /> تأیید
                  </button>
                  <button
                    v-if="c.verification_status !== 'rejected'"
                    class="flex h-9 items-center gap-1 border border-red-600 px-3 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                    :disabled="busy === c.id"
                    @click="startReject(c.id)"
                  >
                    <ShieldX :size="14" /> رد
                  </button>
                </div>
              </td>
            </tr>
            <!-- Reject reason input (inline row) -->
            <tr v-if="rejectingId === c.id" class="border-t border-line bg-red-50">
              <td colspan="7" class="p-3">
                <div class="flex flex-wrap items-center gap-2">
                  <input
                    v-model="rejectReason"
                    type="text"
                    placeholder="دلیل رد (اختیاری)"
                    class="form-control flex-1"
                    @keyup.enter="verify(c, 'rejected', rejectReason)"
                  />
                  <button
                    class="h-10 bg-red-600 px-4 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                    :disabled="busy === c.id"
                    @click="verify(c, 'rejected', rejectReason)"
                  >
                    ثبت رد
                  </button>
                  <button
                    class="h-10 border border-line px-4 text-sm hover:border-gold"
                    @click="cancelReject"
                  >
                    انصراف
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Mobile cards -->
    <div class="space-y-3 md:hidden">
      <div
        v-for="c in data"
        :key="c.id"
        class="admin-card p-4"
      >
        <div class="flex items-start justify-between gap-2">
          <div>
            <p class="font-medium">{{ c.full_name ?? '—' }}</p>
            <p class="tnum mt-1 text-sm text-ink-muted" dir="ltr">{{ c.phone }}</p>
            <p class="mt-1 text-sm text-ink-muted">{{ c.store_name ?? '—' }}</p>
            <p class="tnum mt-1 text-xs text-ink-muted">{{ faDate(c.created_at) }}</p>
          </div>
          <span class="shrink-0 px-2 py-1 text-xs" :class="STATUS_CLASS[c.verification_status]">
            {{ STATUS_LABEL[c.verification_status] }}
          </span>
        </div>

        <!-- Documents -->
        <div v-if="c.verification_documents.length" class="mt-3 flex flex-wrap gap-2">
          <a
            v-for="(doc, i) in c.verification_documents"
            :key="i"
            :href="doc.url"
            target="_blank"
            rel="noopener"
            :title="doc.filename ?? `سند ${toFa(i + 1)}`"
          >
            <img
              v-if="isImage(doc.url)"
              :src="doc.url"
              :alt="doc.filename ?? `سند ${toFa(i + 1)}`"
              class="h-16 w-16 rounded border border-line object-cover"
            />
            <span
              v-else
              class="flex h-12 w-24 items-center justify-center border border-line bg-surface-soft text-xs text-ink-muted"
            >
              {{ doc.filename ?? `سند ${toFa(i + 1)}` }}
            </span>
          </a>
        </div>

        <!-- Actions -->
        <div class="mt-3 flex flex-wrap gap-2">
          <button
            v-if="c.verification_status !== 'approved'"
            class="flex h-9 items-center gap-1 bg-green-700 px-3 text-xs text-white hover:bg-green-800 disabled:opacity-50"
            :disabled="busy === c.id"
            @click="verify(c, 'approved')"
          >
            <ShieldCheck :size="14" /> تأیید
          </button>
          <button
            v-if="c.verification_status !== 'rejected'"
            class="flex h-9 items-center gap-1 border border-red-600 px-3 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
            :disabled="busy === c.id"
            @click="startReject(c.id)"
          >
            <ShieldX :size="14" /> رد
          </button>
        </div>

        <!-- Reject reason -->
        <div v-if="rejectingId === c.id" class="mt-3 flex flex-wrap gap-2">
          <input
            v-model="rejectReason"
            type="text"
            placeholder="دلیل رد (اختیاری)"
            class="form-control flex-1"
          />
          <button
            class="h-10 bg-red-600 px-4 text-sm text-white hover:bg-red-700 disabled:opacity-50"
            :disabled="busy === c.id"
            @click="verify(c, 'rejected', rejectReason)"
          >
            ثبت رد
          </button>
          <button class="h-10 border border-line px-4 text-sm hover:border-gold" @click="cancelReject">
            انصراف
          </button>
        </div>
      </div>
    </div>

    <p v-if="!data?.length" class="py-12 text-center text-ink-muted">مشتری‌ای یافت نشد.</p>
  </div>
</template>
