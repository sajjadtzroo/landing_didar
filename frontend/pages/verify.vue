<script setup lang="ts">
import { BadgeCheck, Banknote, Search, ShieldAlert, ShieldCheck } from 'lucide-vue-next'
import { onMounted, reactive, ref } from 'vue'
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

// Passport timeline labels (unknown types are hidden rather than shown raw).
const EVENT_LABEL: Record<string, string> = {
  minted: 'صدور کد اصالت',
  sold: 'فروش و تحویل',
  warranty_activated: 'فعال‌سازی گارانتی',
  buyback_requested: 'ثبت درخواست بازخرید',
}

const BUYBACK_LABEL: Record<string, string> = {
  under_review: 'درخواست بازخرید در حال بررسی',
  accepted: 'درخواست بازخرید پذیرفته شد',
  rejected: 'درخواست بازخرید رد شد',
}

// --- Warranty activation + buyback request (WO 7.8 / 7.9) ---
const { toast } = useToast()
const who = reactive({ full_name: '', phone: '' })
const warrantyFormOpen = ref(false)
const buybackFormOpen = ref(false)
const buybackNote = ref('')
const acting = ref(false)
const actionError = ref('')

async function activateWarranty() {
  acting.value = true
  actionError.value = ''
  try {
    await $fetch(`/serials/${result.value!.code}/warranty`, {
      method: 'POST',
      baseURL: useApiBase(),
      body: { full_name: who.full_name, phone: who.phone },
    })
    toast('گارانتی فعال شد')
    warrantyFormOpen.value = false
    await verify()
  } catch (e: any) {
    actionError.value = e?.data?.detail || 'فعال‌سازی ناموفق بود.'
  } finally {
    acting.value = false
  }
}

async function requestBuyback() {
  acting.value = true
  actionError.value = ''
  try {
    await $fetch(`/serials/${result.value!.code}/buyback`, {
      method: 'POST',
      baseURL: useApiBase(),
      body: { full_name: who.full_name, phone: who.phone, note: buybackNote.value || null },
    })
    toast('درخواست بازخرید ثبت شد')
    buybackFormOpen.value = false
    await verify()
  } catch (e: any) {
    actionError.value = e?.data?.detail || 'ثبت درخواست ناموفق بود.'
  } finally {
    acting.value = false
  }
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
          autocomplete="off"
          enterkeyhint="search"
          placeholder="DGV-XXXXXXXX"
          aria-label="کد اصالت"
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

        <!-- Passport timeline -->
        <div
          v-if="result.events?.some((e) => EVENT_LABEL[e.type])"
          class="border-t border-line px-4 py-3"
        >
          <p class="mb-2 text-xs text-ink-muted">شناسنامه قطعه</p>
          <ol class="space-y-1.5">
            <li
              v-for="(e, i) in result.events.filter((ev) => EVENT_LABEL[ev.type])"
              :key="i"
              class="flex items-center gap-2 text-sm text-ink"
            >
              <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-gold" aria-hidden="true" />
              {{ EVENT_LABEL[e.type] }}
              <span class="tnum ms-auto text-xs text-ink-muted">{{ faDate(e.at) }}</span>
            </li>
          </ol>
        </div>

        <!-- Warranty (WO 7.8) -->
        <div class="border-t border-line px-4 py-3">
          <div v-if="result.warranty" class="flex items-center gap-2 text-sm">
            <ShieldCheck :size="18" :class="result.warranty.active ? 'text-success' : 'text-ink-muted'" />
            <span :class="result.warranty.active ? 'text-success' : 'text-ink-muted'">
              {{ result.warranty.active ? 'گارانتی فعال است' : 'گارانتی منقضی شده' }}
            </span>
            <span class="tnum ms-auto text-xs text-ink-muted">تا {{ faDate(result.warranty.expires_at) }}</span>
          </div>

          <template v-else-if="result.warranty_available">
            <button
              v-if="!warrantyFormOpen"
              type="button"
              class="flex h-11 w-full items-center justify-center gap-2 bg-navy text-sm font-medium text-white hover:bg-gold"
              @click="warrantyFormOpen = true; buybackFormOpen = false; actionError = ''"
            >
              <ShieldCheck :size="16" /> فعال‌سازی گارانتی
            </button>
            <form v-else class="space-y-3" novalidate @submit.prevent="activateWarranty">
              <p class="text-xs text-ink-muted">برای فعال‌سازی گارانتی ۱۲ ماهه، مشخصات خود را وارد کنید.</p>
              <FormField label="نام و نام خانوادگی" required v-slot="{ id }">
                <input :id="id" v-model="who.full_name" type="text" autocomplete="name" enterkeyhint="next" class="form-control h-11" />
              </FormField>
              <FormField label="شماره موبایل" required v-slot="{ id }">
                <input :id="id" v-model="who.phone" type="tel" dir="ltr" inputmode="numeric" autocomplete="tel" maxlength="11" enterkeyhint="done" placeholder="09xxxxxxxxx" class="form-control h-11 text-start" />
              </FormField>
              <p v-if="actionError" role="alert" class="text-xs text-danger">{{ actionError }}</p>
              <button
                type="submit"
                class="flex h-11 w-full items-center justify-center bg-navy text-sm font-medium text-white hover:bg-gold disabled:opacity-60"
                :disabled="acting || who.full_name.trim().length < 3 || !who.phone"
              >
                {{ acting ? 'در حال ثبت…' : 'فعال‌سازی' }}
              </button>
            </form>
          </template>
        </div>

        <!-- Buyback (WO 7.9) -->
        <div class="border-t border-line px-4 py-3">
          <p v-if="result.buyback_status" class="flex items-center gap-2 text-sm text-ink-muted">
            <Banknote :size="18" class="text-gold-text" />
            {{ BUYBACK_LABEL[result.buyback_status] }}
          </p>
          <template v-if="result.buyback_status !== 'under_review'">
            <button
              v-if="!buybackFormOpen"
              type="button"
              class="mt-2 flex h-11 w-full items-center justify-center gap-2 border border-line text-sm hover:border-gold"
              @click="buybackFormOpen = true; warrantyFormOpen = false; actionError = ''"
            >
              <Banknote :size="16" /> درخواست بازخرید
            </button>
            <form v-else class="mt-2 space-y-3" novalidate @submit.prevent="requestBuyback">
              <p class="text-xs text-ink-muted">کارشناسان دیدار پس از بررسی با شما تماس می‌گیرند.</p>
              <FormField label="نام و نام خانوادگی" required v-slot="{ id }">
                <input :id="id" v-model="who.full_name" type="text" autocomplete="name" enterkeyhint="next" class="form-control h-11" />
              </FormField>
              <FormField label="شماره موبایل" required v-slot="{ id }">
                <input :id="id" v-model="who.phone" type="tel" dir="ltr" inputmode="numeric" autocomplete="tel" maxlength="11" enterkeyhint="next" placeholder="09xxxxxxxxx" class="form-control h-11 text-start" />
              </FormField>
              <FormField label="توضیحات (اختیاری)" v-slot="{ id }">
                <input :id="id" v-model="buybackNote" type="text" maxlength="300" enterkeyhint="done" class="form-control h-11" />
              </FormField>
              <p v-if="actionError" role="alert" class="text-xs text-danger">{{ actionError }}</p>
              <button
                type="submit"
                class="flex h-11 w-full items-center justify-center bg-navy text-sm font-medium text-white hover:bg-gold disabled:opacity-60"
                :disabled="acting || who.full_name.trim().length < 3 || !who.phone"
              >
                {{ acting ? 'در حال ثبت…' : 'ثبت درخواست' }}
              </button>
            </form>
          </template>
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
