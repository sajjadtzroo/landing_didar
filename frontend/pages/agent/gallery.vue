<script setup lang="ts">
import { Banknote } from 'lucide-vue-next'
import { computed, reactive, ref } from 'vue'
import type { GalleryItem, GalleryResponse } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'agent', middleware: 'agent' })

const KIND_LABEL = { sample: 'نمونه', sellable: 'قابل فروش' } as const
const STATUS_LABEL = { with_agent: 'همراه من', returned: 'برگشتی', sold: 'فروخته‌شده' } as const

const mediaUrl = useMediaUrl()
const { toast } = useToast()

const { data, refresh } = await useAsyncData('agent-gallery', () =>
  apiFetch<GalleryResponse>('/agent/gallery'),
)
const carried = computed(() => (data.value?.items || []).filter((i) => i.status === 'with_agent'))
const history = computed(() => (data.value?.items || []).filter((i) => i.status !== 'with_agent'))

// --- Quick sale ---
const sellOpen = ref(false)
const sell = reactive({ id: '', code: '', product: '', note: '' })
const selling = ref(false)

function startSell(i: GalleryItem) {
  sell.id = i.id
  sell.code = i.code
  sell.product = i.product_name
  sell.note = ''
  sellOpen.value = true
}
async function confirmSell() {
  selling.value = true
  try {
    await apiFetch(`/agent/gallery/${sell.id}/sell`, {
      method: 'POST',
      body: { note: sell.note || null },
    })
    toast('فروش ثبت شد')
    sellOpen.value = false
    await refresh()
  } finally {
    selling.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-1 text-xl font-medium">گالری من</h1>
    <p class="mb-4 text-sm text-ink-muted">کالاهایی که همراه دارید؛ فروش فوری فقط برای اقلام قابل فروش.</p>

    <div v-if="data" class="mb-5 flex flex-wrap gap-2 text-sm">
      <span class="corner-soft border border-line bg-surface-raised px-3 py-1.5">
        همراه من: <span class="tnum font-medium text-gold-text">{{ toFa(data.counts.with_agent) }}</span>
      </span>
      <span class="corner-soft border border-line bg-surface-raised px-3 py-1.5">
        فروخته‌شده: <span class="tnum font-medium text-gold-text">{{ toFa(data.counts.sold) }}</span>
      </span>
    </div>

    <div class="space-y-3">
      <div v-for="i in carried" :key="i.id" class="corner-soft flex items-center gap-3 border border-line bg-surface-raised p-3">
        <div class="h-14 w-14 shrink-0 overflow-hidden bg-media-surface">
          <img v-if="i.image_url" :src="mediaUrl(i.image_url)" :alt="i.product_name" class="h-full w-full object-cover" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink">{{ i.product_name }}</p>
          <p class="tnum text-xs text-gold-text" dir="ltr">{{ i.code }}</p>
          <span
            class="mt-1 inline-block px-2 py-0.5 text-[11px]"
            :class="i.kind === 'sample' ? 'bg-surface-soft text-ink-muted' : 'bg-success-soft text-success'"
          >{{ KIND_LABEL[i.kind] }}</span>
        </div>
        <button
          v-if="i.kind === 'sellable'"
          class="flex h-10 shrink-0 items-center gap-1.5 bg-navy px-3 text-xs font-medium text-white hover:bg-gold"
          @click="startSell(i)"
        >
          <Banknote :size="14" /> فروش فوری
        </button>
      </div>
    </div>

    <p v-if="data && !carried.length" class="corner-soft border border-line bg-surface-raised py-12 text-center text-sm text-ink-muted">
      در حال حاضر کالایی همراه شما ثبت نشده است.
    </p>

    <template v-if="history.length">
      <h2 class="mb-2 mt-8 text-sm text-ink-muted">سوابق</h2>
      <ul class="space-y-2">
        <li v-for="i in history" :key="i.id" class="flex items-center justify-between border border-line bg-surface p-3 text-sm">
          <span class="min-w-0 flex-1 truncate">{{ i.product_name }} <span class="tnum text-xs text-ink-muted" dir="ltr">{{ i.code }}</span></span>
          <span class="text-xs text-ink-muted">{{ STATUS_LABEL[i.status] }}</span>
        </li>
      </ul>
    </template>

    <!-- Quick-sale sheet -->
    <BaseSheet v-model="sellOpen" :title="`فروش فوری — ${sell.code}`">
      <div class="space-y-4">
        <p class="text-sm text-ink-muted">{{ sell.product }}</p>
        <FormField label="خریدار / توضیح (اختیاری)" v-slot="{ id }">
          <input :id="id" v-model="sell.note" maxlength="300" class="form-control" />
        </FormField>
        <p class="text-xs text-ink-muted">
          با ثبت فروش، وضعیت این قطعه «فروخته‌شده» می‌شود و در شناسنامه آن ثبت می‌گردد.
        </p>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="selling"
          @click="confirmSell"
        >
          {{ selling ? 'در حال ثبت…' : 'ثبت فروش' }}
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
