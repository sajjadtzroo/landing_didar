<script setup lang="ts">
import {
  ArrowDown, ArrowRight, ArrowUp, ExternalLink, Plus, Trash2, Upload, X,
} from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { AdminLanding, Product } from '~/types'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const id = route.params.id as string

const { data: landing } = await useAsyncData(`admin-landing-${id}`, () =>
  apiFetch<AdminLanding>(`/admin/landings/${id}`),
)
const { data: products } = await useAsyncData('admin-all-products', () =>
  apiFetch<Product[]>('/admin/products'),
)
if (!landing.value) {
  throw createError({ statusCode: 404, statusMessage: 'Landing not found', fatal: true })
}

const productById = computed(() =>
  Object.fromEntries((products.value ?? []).map((p) => [p.id, p])) as Record<string, Product>,
)

// Trust icons the editor exposes — MUST match TrustBar's whitelist.
const TRUST_ICONS = [
  'BadgeCheck', 'FileCheck', 'RefreshCw', 'ShieldCheck', 'Award', 'Gem', 'Truck', 'Handshake', 'Sparkles',
]
const SECTION_LABELS: Record<string, string> = {
  promo: 'نوار تخفیف', hero: 'هیرو', trust: 'کارت‌های اعتماد',
  products: 'محصولات', faq: 'سؤالات متداول', footer: 'فوتر',
}

// --- Editable state (normalized so every field/array exists) ---
const raw = (landing.value.content || {}) as any
const meta = reactive({
  title: landing.value.title || '',
  hero_video_url: landing.value.hero_video_url || '',
  hero_poster_url: landing.value.hero_poster_url || '',
})
const content = reactive({
  sections: {
    promo: true, hero: true, trust: true, products: true, faq: true, footer: true,
    ...(raw.sections || {}),
  } as Record<string, boolean>,
  promo: { text: raw.promo?.text ?? '' },
  hero: { eyebrow: '', headline: '', supporting: '', cta: '', ...(raw.hero || {}) },
  trust: (Array.isArray(raw.trust) ? raw.trust : []).map((t: any) => ({
    icon: t?.icon || 'BadgeCheck', title: t?.title || '', sub: t?.sub || '',
  })),
  groups: (Array.isArray(raw.groups) ? raw.groups : []).map((g: any) => ({
    title: g?.title || '', eyebrow: g?.eyebrow || '', description: g?.description || '',
    product_ids: Array.isArray(g?.product_ids) ? [...g.product_ids] : [],
  })),
  faq: (Array.isArray(raw.faq) ? raw.faq : []).map((f: any) => ({
    question: f?.question || '', answer: f?.answer || '',
  })),
  footer: {
    tagline: '', address: '', hours: '', phone: '', phoneDisplay: '', email: '',
    whatsapp: '', telegram: '', instagram: '', rights: '', ...(raw.footer || {}),
  },
})

// --- Generic list helpers ---
function move(arr: any[], i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= arr.length) return
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}
function removeAt(arr: any[], i: number) {
  arr.splice(i, 1)
}

// --- Trust ---
function addTrust() {
  content.trust.push({ icon: 'BadgeCheck', title: '', sub: '' })
}
// --- Groups + product picker ---
function addGroup() {
  content.groups.push({ title: 'گروه جدید', eyebrow: '', description: '', product_ids: [] })
}
function availableFor(g: any): Product[] {
  return (products.value ?? []).filter((p) => !g.product_ids.includes(p.id))
}
function addProduct(g: any, pid: string) {
  if (pid && !g.product_ids.includes(pid)) g.product_ids.push(pid)
}
// --- FAQ ---
function addFaq() {
  content.faq.push({ question: '', answer: '' })
}

// --- Media upload ---
const { upload } = useAdminUpload()
const uploading = ref('')
async function pickMedia(e: Event, field: 'hero_video_url' | 'hero_poster_url') {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = field
  try {
    meta[field] = await upload(file)
  } catch {
    alert('بارگذاری فایل ناموفق بود.')
  } finally {
    uploading.value = ''
    ;(e.target as HTMLInputElement).value = ''
  }
}

// --- Save / delete ---
const saving = ref(false)
const saved = ref(false)
async function save() {
  saving.value = true
  saved.value = false
  try {
    await apiFetch(`/admin/landings/${id}`, {
      method: 'PATCH',
      body: {
        title: meta.title,
        hero_video_url: meta.hero_video_url || null,
        hero_poster_url: meta.hero_poster_url || null,
        content: JSON.parse(JSON.stringify(content)),
      },
    })
    saved.value = true
  } catch {
    alert('ذخیره ناموفق بود.')
  } finally {
    saving.value = false
  }
}
async function removeLanding() {
  if (!confirm('این صفحه فرود حذف شود؟')) return
  await apiFetch(`/admin/landings/${id}`, { method: 'DELETE' })
  await navigateTo('/admin/landings')
}
</script>

<template>
  <div class="pb-28">
    <!-- Header -->
    <div class="mb-6 flex flex-wrap items-center gap-3">
      <NuxtLink
        to="/admin/landings"
        class="flex h-10 w-10 items-center justify-center text-ink-muted hover:text-ink"
        aria-label="بازگشت"
      >
        <ArrowRight :size="18" />
      </NuxtLink>
      <div class="min-w-0 flex-1">
        <h1 class="truncate text-2xl font-medium">{{ meta.title || 'ویرایش صفحه' }}</h1>
        <p class="tnum text-xs text-ink-muted" dir="ltr">/l/{{ landing?.slug }}</p>
      </div>
      <a
        :href="`/l/${landing?.slug}`"
        target="_blank"
        rel="noopener"
        class="flex h-11 items-center gap-2 border border-line px-4 text-sm hover:border-gold-soft"
      >
        <ExternalLink :size="15" /> پیش‌نمایش
      </a>
      <button
        class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger"
        aria-label="حذف صفحه"
        @click="removeLanding"
      >
        <Trash2 :size="16" />
      </button>
    </div>

    <div class="space-y-6">
      <!-- Basics -->
      <section class="admin-card space-y-4">
        <h2 class="text-lg font-medium">مشخصات</h2>
        <FormField label="عنوان" v-slot="{ id: fid }">
          <input :id="fid" v-model="meta.title" class="form-control" />
        </FormField>
        <FormField label="اسلاگ (غیرقابل تغییر)" v-slot="{ id: fid }">
          <input :id="fid" :value="landing?.slug" dir="ltr" class="form-control opacity-60" disabled />
        </FormField>
      </section>

      <!-- Hero -->
      <section class="admin-card space-y-4">
        <label class="flex items-center justify-between">
          <h2 class="text-lg font-medium">هیرو</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="content.sections.hero" type="checkbox" class="h-4 w-4" /> نمایش
          </span>
        </label>
        <FormField label="روتیتر (Eyebrow)" v-slot="{ id: fid }">
          <input :id="fid" v-model="content.hero.eyebrow" class="form-control" />
        </FormField>
        <FormField label="تیتر اصلی" v-slot="{ id: fid }">
          <input :id="fid" v-model="content.hero.headline" class="form-control" />
        </FormField>
        <FormField label="زیرنویس" v-slot="{ id: fid }">
          <textarea :id="fid" v-model="content.hero.supporting" rows="2" class="form-control" />
        </FormField>
        <FormField label="متن دکمه" v-slot="{ id: fid }">
          <input :id="fid" v-model="content.hero.cta" class="form-control" />
        </FormField>

        <!-- Media -->
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <p class="mb-1.5 text-sm">ویدیوی هیرو</p>
            <input v-model="meta.hero_video_url" dir="ltr" class="form-control" placeholder="/media/hero.mp4" />
            <label class="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs text-gold-text hover:underline">
              <Upload :size="14" />
              {{ uploading === 'hero_video_url' ? 'در حال بارگذاری…' : 'بارگذاری ویدیو' }}
              <input type="file" accept="video/mp4,video/webm" class="hidden" @change="pickMedia($event, 'hero_video_url')" />
            </label>
          </div>
          <div>
            <p class="mb-1.5 text-sm">تصویر پوستر</p>
            <input v-model="meta.hero_poster_url" dir="ltr" class="form-control" placeholder="/media/hero-poster.jpg" />
            <label class="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs text-gold-text hover:underline">
              <Upload :size="14" />
              {{ uploading === 'hero_poster_url' ? 'در حال بارگذاری…' : 'بارگذاری تصویر' }}
              <input type="file" accept="image/*" class="hidden" @change="pickMedia($event, 'hero_poster_url')" />
            </label>
            <NuxtImg v-if="meta.hero_poster_url" :src="meta.hero_poster_url" alt="" class="mt-2 h-24 w-full object-cover" />
          </div>
        </div>
      </section>

      <!-- Promo -->
      <section class="admin-card space-y-4">
        <label class="flex items-center justify-between">
          <h2 class="text-lg font-medium">{{ SECTION_LABELS.promo }}</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="content.sections.promo" type="checkbox" class="h-4 w-4" /> نمایش
          </span>
        </label>
        <FormField label="متن نوار تخفیف" v-slot="{ id: fid }">
          <input :id="fid" v-model="content.promo.text" class="form-control" />
        </FormField>
      </section>

      <!-- Trust -->
      <section class="admin-card space-y-4">
        <label class="flex items-center justify-between">
          <h2 class="text-lg font-medium">{{ SECTION_LABELS.trust }}</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="content.sections.trust" type="checkbox" class="h-4 w-4" /> نمایش
          </span>
        </label>
        <div
          v-for="(t, i) in content.trust"
          :key="i"
          class="grid items-end gap-3 border border-line p-3 sm:grid-cols-[8rem,1fr,1fr,auto]"
        >
          <label class="text-xs text-ink-muted">
            آیکون
            <select v-model="t.icon" class="form-control mt-1">
              <option v-for="ic in TRUST_ICONS" :key="ic" :value="ic">{{ ic }}</option>
            </select>
          </label>
          <label class="text-xs text-ink-muted">
            عنوان
            <input v-model="t.title" class="form-control mt-1" />
          </label>
          <label class="text-xs text-ink-muted">
            زیرعنوان
            <input v-model="t.sub" class="form-control mt-1" />
          </label>
          <button
            class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger"
            aria-label="حذف"
            @click="removeAt(content.trust, i)"
          >
            <X :size="16" />
          </button>
        </div>
        <button class="flex items-center gap-2 text-sm text-gold-text hover:underline" @click="addTrust">
          <Plus :size="15" /> افزودن کارت
        </button>
      </section>

      <!-- Product groups -->
      <section class="admin-card space-y-4">
        <label class="flex items-center justify-between">
          <h2 class="text-lg font-medium">{{ SECTION_LABELS.products }} (پورتفولیو)</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="content.sections.products" type="checkbox" class="h-4 w-4" /> نمایش
          </span>
        </label>

        <div v-for="(g, gi) in content.groups" :key="gi" class="space-y-3 border border-line p-4">
          <div class="flex items-center gap-2">
            <p class="flex-1 text-sm font-medium">گروه {{ gi + 1 }}</p>
            <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="gi === 0" aria-label="بالا" @click="move(content.groups, gi, -1)"><ArrowUp :size="15" /></button>
            <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="gi === content.groups.length - 1" aria-label="پایین" @click="move(content.groups, gi, 1)"><ArrowDown :size="15" /></button>
            <button class="text-ink-muted hover:text-danger" aria-label="حذف گروه" @click="removeAt(content.groups, gi)"><Trash2 :size="15" /></button>
          </div>
          <div class="grid gap-3 sm:grid-cols-3">
            <input v-model="g.title" class="form-control" placeholder="عنوان گروه" />
            <input v-model="g.eyebrow" class="form-control" placeholder="روتیتر" />
            <input v-model="g.description" class="form-control" placeholder="توضیح کوتاه" />
          </div>

          <!-- Selected products (ordered) -->
          <ul v-if="g.product_ids.length" class="space-y-1.5">
            <li
              v-for="(pid, pi) in g.product_ids"
              :key="pid"
              class="flex items-center gap-2 border border-line bg-surface p-2 text-sm"
            >
              <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="pi === 0" aria-label="بالا" @click="move(g.product_ids, pi, -1)"><ArrowUp :size="13" /></button>
              <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="pi === g.product_ids.length - 1" aria-label="پایین" @click="move(g.product_ids, pi, 1)"><ArrowDown :size="13" /></button>
              <span class="min-w-0 flex-1 truncate">{{ productById[pid]?.name || pid }}</span>
              <button class="text-ink-muted hover:text-danger" aria-label="حذف" @click="removeAt(g.product_ids, pi)"><X :size="14" /></button>
            </li>
          </ul>
          <p v-else class="text-xs text-ink-muted">محصولی در این گروه نیست.</p>

          <select
            class="form-control"
            @change="addProduct(g, ($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''"
          >
            <option value="">افزودن محصول…</option>
            <option v-for="p in availableFor(g)" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <button class="flex items-center gap-2 text-sm text-gold-text hover:underline" @click="addGroup">
          <Plus :size="15" /> افزودن گروه
        </button>
      </section>

      <!-- FAQ -->
      <section class="admin-card space-y-4">
        <label class="flex items-center justify-between">
          <h2 class="text-lg font-medium">{{ SECTION_LABELS.faq }}</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="content.sections.faq" type="checkbox" class="h-4 w-4" /> نمایش
          </span>
        </label>
        <div v-for="(f, i) in content.faq" :key="i" class="space-y-2 border border-line p-3">
          <div class="flex items-center gap-2">
            <span class="tnum flex-1 text-xs text-ink-muted">سؤال {{ i + 1 }}</span>
            <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="i === 0" aria-label="بالا" @click="move(content.faq, i, -1)"><ArrowUp :size="14" /></button>
            <button class="text-ink-muted hover:text-ink disabled:opacity-30" :disabled="i === content.faq.length - 1" aria-label="پایین" @click="move(content.faq, i, 1)"><ArrowDown :size="14" /></button>
            <button class="text-ink-muted hover:text-danger" aria-label="حذف" @click="removeAt(content.faq, i)"><X :size="15" /></button>
          </div>
          <input v-model="f.question" class="form-control" placeholder="سؤال" />
          <textarea v-model="f.answer" rows="2" class="form-control" placeholder="پاسخ" />
        </div>
        <button class="flex items-center gap-2 text-sm text-gold-text hover:underline" @click="addFaq">
          <Plus :size="15" /> افزودن سؤال
        </button>
      </section>

      <!-- Footer -->
      <section class="admin-card space-y-4">
        <label class="flex items-center justify-between">
          <h2 class="text-lg font-medium">{{ SECTION_LABELS.footer }}</h2>
          <span class="flex items-center gap-2 text-sm text-ink-muted">
            <input v-model="content.sections.footer" type="checkbox" class="h-4 w-4" /> نمایش
          </span>
        </label>
        <div class="grid gap-3 sm:grid-cols-2">
          <input v-model="content.footer.tagline" class="form-control" placeholder="شعار" />
          <input v-model="content.footer.address" class="form-control" placeholder="نشانی" />
          <input v-model="content.footer.hours" class="form-control" placeholder="ساعات کاری" />
          <input v-model="content.footer.phone" dir="ltr" class="form-control" placeholder="+98..." />
          <input v-model="content.footer.phoneDisplay" dir="ltr" class="form-control" placeholder="۰۲۱…" />
          <input v-model="content.footer.email" dir="ltr" class="form-control" placeholder="email" />
          <input v-model="content.footer.whatsapp" dir="ltr" class="form-control" placeholder="WhatsApp URL" />
          <input v-model="content.footer.telegram" dir="ltr" class="form-control" placeholder="Telegram URL" />
          <input v-model="content.footer.instagram" dir="ltr" class="form-control" placeholder="Instagram URL" />
          <input v-model="content.footer.rights" class="form-control" placeholder="متن حقوق" />
        </div>
      </section>
    </div>

    <!-- Sticky save bar -->
    <div class="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 px-5 py-3 backdrop-blur lg:pe-72">
      <div class="mx-auto flex max-w-4xl items-center gap-3">
        <span v-if="saved" class="text-sm text-success">ذخیره شد ✓</span>
        <div class="flex-1" />
        <button
          class="flex h-12 items-center justify-center bg-navy px-8 text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'در حال ذخیره…' : 'ذخیره تغییرات' }}
        </button>
      </div>
    </div>
  </div>
</template>
