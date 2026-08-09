<script setup lang="ts">
import { BadgeCheck, Search, ShieldAlert } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import type { SerialVerify } from '~/types'
import { toFa } from '~/utils/format'

const route = useRoute()
const code = ref('')
const result = ref<SerialVerify | null>(null)
const notFound = ref(false)
const loading = ref(false)
const searched = ref(false)

// Display formatting: uppercase, strip separators, re-insert one dash after DGV.
function format(raw: string) {
  const c = raw.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 11)
  return c.length > 3 ? `${c.slice(0, 3)}-${c.slice(3)}` : c
}
function onInput(e: Event) {
  code.value = format((e.target as HTMLInputElement).value)
}

async function verify() {
  const c = code.value.trim()
  if (!c) return
  loading.value = true
  notFound.value = false
  result.value = null
  try {
    result.value = await $fetch<SerialVerify>('/serials/verify', {
      baseURL: useApiBase(),
      query: { code: c },
    })
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
    searched.value = true
  }
}

onMounted(() => {
  // QR / deep-link support: /verify?code=DGV-XXXX auto-checks.
  const q = route.query.code
  if (typeof q === 'string' && q) {
    code.value = format(q)
    verify()
  }
})

useHead({ title: 'بررسی اصالت | دیدار گلد' })

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <main class="pt-16 sm:pt-28">
    <div class="mx-auto max-w-md px-5 pb-24 sm:px-10">
      <div class="text-center">
        <BadgeCheck :size="40" class="mx-auto text-gold-text" aria-hidden="true" />
        <h1 class="mt-3 text-2xl font-medium text-ink">بررسی اصالت محصول</h1>
        <p class="mt-2 text-sm leading-7 text-ink-muted">
          کد اصالت درج‌شده روی کارت ضمانت قطعه را وارد کنید تا اصل بودن آن را بررسی کنید.
        </p>
      </div>

      <form class="mt-6 flex gap-2" novalidate @submit.prevent="verify">
        <input
          :value="code"
          dir="ltr"
          inputmode="text"
          autocapitalize="characters"
          placeholder="DGV-XXXXXXXX"
          class="form-control text-center tracking-widest"
          @input="onInput"
        />
        <button
          type="submit"
          class="flex h-14 shrink-0 items-center gap-2 bg-navy px-5 text-sm font-medium text-white transition hover:bg-gold disabled:opacity-60"
          :disabled="loading || !code"
        >
          <Search :size="16" /> {{ loading ? '…' : 'بررسی' }}
        </button>
      </form>

      <!-- Genuine -->
      <div v-if="result" class="mt-8 border border-gold/40 bg-surface-raised">
        <div class="flex items-center gap-2 border-b border-line bg-success-soft px-4 py-3 text-success">
          <BadgeCheck :size="20" /> <span class="font-medium">اصل و معتبر</span>
        </div>
        <div class="flex gap-4 p-4">
          <div class="h-24 w-24 shrink-0 overflow-hidden bg-media-surface">
            <NuxtImg v-if="result.image_url" :src="result.image_url" :alt="result.product_name" class="h-full w-full object-cover" width="96" height="96" />
          </div>
          <div class="min-w-0">
            <p class="text-lg font-medium text-ink">{{ result.product_name }}</p>
            <p class="tnum mt-1 text-sm text-ink-muted">
              <template v-if="result.karat">{{ toFa(result.karat) }} عیار</template>
              <template v-if="result.weight_grams"> · {{ toFa(Number(result.weight_grams)) }} گرم</template>
            </p>
            <p class="tnum mt-3 text-xs text-ink-muted" dir="ltr">{{ result.code }}</p>
            <p class="tnum mt-1 text-xs text-ink-muted">تاریخ صدور کد: {{ faDate(result.issued_at) }}</p>
          </div>
        </div>
      </div>

      <!-- Not found / invalid -->
      <div v-else-if="searched && notFound" class="mt-8 flex items-start gap-3 border border-danger bg-danger-soft p-4 text-danger">
        <ShieldAlert :size="20" class="mt-0.5 shrink-0" />
        <div>
          <p class="font-medium">این کد معتبر نیست</p>
          <p class="mt-1 text-sm">کد واردشده یافت نشد یا باطل شده است. لطفاً کد را دوباره بررسی کنید یا با ما تماس بگیرید.</p>
        </div>
      </div>
    </div>
  </main>
</template>
