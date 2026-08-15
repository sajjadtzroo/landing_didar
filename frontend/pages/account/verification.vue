<script setup lang="ts">
import { ExternalLink, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

definePageMeta({ middleware: 'customer' })

const { customer, ensure } = useCustomerAuth()
const { upload, remove } = useCustomerUpload()
// Local uploads are backend-relative "/media/..."; resolve to the API host.
const mediaUrl = useMediaUrl()

const fullName = ref('')
const storeName = ref('')
const savingProfile = ref(false)
const profileSaved = ref(false)
const uploading = ref(false)
const removing = ref<number | null>(null)

onMounted(async () => {
  await ensure()
  fullName.value = customer.value?.full_name || ''
  storeName.value = customer.value?.store_name || ''
})

const STATUS_LABELS: Record<string, string> = {
  unverified: 'تأیید نشده',
  pending: 'در انتظار بررسی',
  approved: 'تأیید شده',
  rejected: 'رد شده',
}

const STATUS_CLASSES: Record<string, string> = {
  unverified: 'bg-surface-raised text-ink-muted',
  pending: 'bg-gold/20 text-ink',
  approved: 'bg-success/20 text-success',
  rejected: 'bg-danger/20 text-danger',
}

async function saveProfile() {
  savingProfile.value = true
  profileSaved.value = false
  try {
    await apiFetch('/account/me', {
      method: 'PATCH',
      body: { full_name: fullName.value, store_name: storeName.value },
    })
    if (customer.value) {
      customer.value.full_name = fullName.value
      customer.value.store_name = storeName.value
    }
    profileSaved.value = true
  } finally {
    savingProfile.value = false
  }
}

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  try {
    await upload(file)
    await ensure(true)
  } finally {
    uploading.value = false
    ;(e.target as HTMLInputElement).value = ''
  }
}

async function onRemove(idx: number) {
  removing.value = idx
  try {
    await remove(idx)
    await ensure(true)
  } finally {
    removing.value = null
  }
}

useHead({ title: 'احراز هویت | دیدار' })
</script>

<template>
  <AccountShell>
    <h2 class="mb-6 text-xl text-ink">احراز هویت</h2>

    <!-- Status badge -->
    <div v-if="customer" class="mb-6 flex items-center gap-3">
      <span class="text-sm text-ink-muted">وضعیت:</span>
      <span
        class="px-3 py-1 text-sm font-medium"
        :class="STATUS_CLASSES[customer.verification_status]"
      >
        {{ STATUS_LABELS[customer.verification_status] }}
      </span>
    </div>

    <!-- Rejection reason -->
    <div
      v-if="customer?.verification_status === 'rejected' && customer.rejection_reason"
      class="mb-6 border border-danger/40 bg-danger/10 p-4 text-sm text-danger"
    >
      <p class="mb-1 font-medium">دلیل رد شدن:</p>
      <p>{{ customer.rejection_reason }}</p>
    </div>

    <!-- Profile mini-form -->
    <form class="max-w-md space-y-4" @submit.prevent="saveProfile">
      <FormField label="نام و نام خانوادگی" v-slot="{ id }">
        <input :id="id" v-model="fullName" type="text" class="form-control" autocomplete="name" />
      </FormField>
      <FormField label="نام فروشگاه" v-slot="{ id }">
        <input :id="id" v-model="storeName" type="text" class="form-control" />
      </FormField>
      <div class="flex items-center gap-3">
        <button
          type="submit"
          class="flex h-11 items-center bg-navy px-5 text-sm text-white hover:bg-gold disabled:opacity-60"
          :disabled="savingProfile"
        >
          ذخیره اطلاعات
        </button>
        <span v-if="profileSaved" class="text-sm text-success">ذخیره شد</span>
      </div>
    </form>

    <!-- Documents list -->
    <h3 class="mb-4 mt-10 text-lg text-ink">مدارک بارگذاری شده</h3>

    <ul v-if="customer?.verification_documents?.length" class="mb-6 space-y-3">
      <li
        v-for="(doc, idx) in customer.verification_documents"
        :key="idx"
        class="flex items-center justify-between border border-line bg-surface-raised p-4"
      >
        <a
          :href="mediaUrl(doc.url)"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-2 text-sm text-ink hover:text-gold"
        >
          <ExternalLink :size="14" aria-hidden="true" />
          {{ doc.filename || `مدرک ${idx + 1}` }}
        </a>
        <button
          v-if="customer.verification_status === 'pending'"
          type="button"
          class="text-ink-muted hover:text-danger disabled:opacity-40"
          aria-label="حذف مدرک"
          :disabled="removing === idx"
          @click="onRemove(idx)"
        >
          <Trash2 :size="16" />
        </button>
      </li>
    </ul>
    <p v-else class="mb-6 text-sm text-ink-muted">مدرکی بارگذاری نشده است.</p>

    <!-- Upload input (hidden when approved) -->
    <div v-if="customer?.verification_status !== 'approved'" class="max-w-md">
      <label class="mb-2 block text-sm text-ink-muted">بارگذاری مدرک (تصویر یا PDF)</label>
      <input
        type="file"
        accept="image/*,application/pdf"
        class="form-control"
        :disabled="uploading"
        @change="onFileChange"
      />
      <p v-if="uploading" class="mt-2 text-sm text-ink-muted">در حال بارگذاری…</p>
    </div>
  </AccountShell>
</template>
