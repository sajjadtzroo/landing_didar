<script setup lang="ts">
import { ArrowRight, Printer } from 'lucide-vue-next'
import { computed } from 'vue'
import type { ProductSerial, SerialListResponse } from '~/types'
import { toFa } from '~/utils/format'

// Label print sheet: a batch (or current filter) laid out as QR labels.
// Standalone layout — the admin sidebar has no business on paper.
definePageMeta({ layout: false, middleware: 'admin' })

const route = useRoute()
const batchId = computed(() => String(route.query.batch_id || ''))

// Pull the whole batch through the paged admin API (a print run can be large).
const { data: serials } = await useAsyncData(
  () => `serial-print-${batchId.value}`,
  async () => {
    const all: ProductSerial[] = []
    let page = 1
    for (;;) {
      const res = await apiFetch<SerialListResponse>(
        `/admin/serials?batch_id=${batchId.value}&page=${page}&page_size=100`,
      )
      all.push(...res.items)
      if (page * res.page_size >= res.total) break
      page++
    }
    return all
  },
)

function qrUrl(code: string) {
  return `${useApiBase()}/serials/${code}/qr.png`
}
function printPage() {
  window.print()
}

useHead({ title: 'چاپ برچسب سریال | دیدار گلد' })
</script>

<template>
  <div class="min-h-dvh bg-white p-6 text-ink" dir="rtl">
    <!-- Screen-only toolbar -->
    <div class="mb-6 flex items-center gap-3 print:hidden">
      <NuxtLink
        to="/admin/serials"
        class="flex h-10 w-10 items-center justify-center text-ink-muted hover:text-ink"
        aria-label="بازگشت"
      >
        <ArrowRight :size="18" />
      </NuxtLink>
      <h1 class="flex-1 text-xl font-medium">
        برچسب‌های اصالت
        <span v-if="serials" class="tnum text-sm text-ink-muted">({{ toFa(serials.length) }} عدد)</span>
      </h1>
      <button
        class="flex h-11 items-center gap-2 bg-navy px-5 text-sm text-white hover:bg-gold"
        @click="printPage"
      >
        <Printer :size="16" /> چاپ
      </button>
    </div>

    <!-- Label grid (break-inside-avoid keeps each label on one page) -->
    <div class="grid grid-cols-3 gap-4 sm:grid-cols-4 print:grid-cols-4">
      <div
        v-for="s in serials"
        :key="s.id"
        class="flex break-inside-avoid flex-col items-center border border-line p-3 text-center"
      >
        <img :src="qrUrl(s.code)" :alt="s.code" class="h-24 w-24" loading="lazy" />
        <p class="tnum mt-2 text-xs font-medium" dir="ltr">{{ s.code }}</p>
        <p class="mt-0.5 line-clamp-1 text-[11px] text-ink-muted">{{ s.product_name }}</p>
      </div>
    </div>

    <p v-if="serials && !serials.length" class="py-16 text-center text-ink-muted print:hidden">
      سریالی در این دسته یافت نشد.
    </p>
  </div>
</template>
