<script setup lang="ts">
// One carousel for ALL curated collections (eid, firooze, …) — replaces the
// stacked per-portfolio product sections on /shop. Two slides per view (per
// the brief), RTL-aware arrows + keyboard, scroll-snap swipe on touch.
// Vue port of the requested shadcn/embla ServiceCarousel: same UX, zero new
// deps — reuses ProductGrid's snap/scrollBy pattern and the design tokens.
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio } from '~/types'

const props = defineProps<{ portfolios: Portfolio[] }>()

const track = ref<HTMLElement | null>(null)

// RTL-aware paging (same trick as ProductGrid): scrollBy is sign-flipped in RTL.
function page(dir: 1 | -1) {
  const el = track.value
  if (!el) return
  const rtl = getComputedStyle(el).direction === 'rtl' ? -1 : 1
  el.scrollBy({ left: dir * rtl * el.clientWidth * 0.9, behavior: 'smooth' })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') { e.preventDefault(); page(-1) }
  else if (e.key === 'ArrowRight') { e.preventDefault(); page(1) }
}

// Card meta: unique product count + a cover fallback from the first product.
const cards = computed(() =>
  props.portfolios.map((pf) => {
    const ids = new Set<string>()
    let fallback: string | null = null
    for (const g of pf.groups) {
      for (const p of g.products) {
        ids.add(p.id)
        if (!fallback && p.image_url) fallback = p.image_url
      }
    }
    return { ...pf, count: ids.size, cover: pf.cover_image_url || fallback }
  }),
)
</script>

<template>
  <section v-if="cards.length" class="mb-10" :aria-label="CONTENT.nav.collections">
    <h2 class="mb-4 text-lg font-medium text-ink sm:text-xl">
      {{ CONTENT.nav.collections }}
    </h2>

    <div
      class="relative"
      role="region"
      aria-roledescription="carousel"
      tabindex="0"
      @keydown="onKeydown"
    >
      <div
        ref="track"
        class="-mx-5 flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-px-5 px-5 pb-2
          sm:mx-0 sm:scroll-px-0 sm:px-0"
      >
        <NuxtLink
          v-for="pf in cards"
          :key="pf.id"
          :to="`/shop/${pf.slug}`"
          role="group"
          aria-roledescription="slide"
          class="corner-soft group relative shrink-0 snap-start basis-[85%] overflow-hidden border
            border-line bg-surface-raised transition duration-300 hover:-translate-y-1
            hover:border-gold hover:shadow-luxury sm:basis-[calc(50%-0.5rem)]"
        >
          <div class="relative aspect-[16/9] overflow-hidden bg-media-surface">
            <NuxtImg
              v-if="pf.cover"
              :src="pf.cover"
              :alt="pf.name"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
              width="640"
              height="360"
              format="webp"
              sizes="(max-width: 640px) 85vw, 45vw"
              loading="lazy"
            />
            <div
              class="absolute inset-0 bg-gradient-to-t from-navy-deep/70 via-navy-deep/10 to-transparent"
              aria-hidden="true"
            />
            <div class="absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 p-4">
              <div class="min-w-0">
                <h3 class="truncate text-lg font-medium text-white drop-shadow">{{ pf.name }}</h3>
                <p class="tnum mt-0.5 text-xs text-white/80">
                  {{ CONTENT.shop.resultCount(pf.count) }}
                </p>
              </div>
              <span
                class="flex shrink-0 items-center gap-1 text-xs font-medium text-gold underline-offset-4
                  group-hover:underline"
              >
                {{ CONTENT.shop.viewCollection }}
                <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
              </span>
            </div>
          </div>

          <!-- Signature gold accent: grows from the start edge on hover -->
          <span
            class="pointer-events-none absolute inset-x-0 bottom-0 h-1 origin-right scale-x-0
              bg-gold transition-transform duration-500 group-hover:scale-x-100"
          />
        </NuxtLink>
      </div>

      <!-- Paging arrows (pointer devices; touch swipes the snap row) -->
      <template v-if="cards.length > 2">
        <button
          type="button"
          class="absolute -start-3 top-1/2 hidden h-10 w-10 -translate-y-1/2 items-center
            justify-center rounded-full border border-line bg-surface text-ink shadow-md transition
            hover:border-gold hover:text-gold-text sm:flex"
          :aria-label="'اسلاید قبلی'"
          @click="page(-1)"
        >
          <ChevronRight :size="20" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="absolute -end-3 top-1/2 hidden h-10 w-10 -translate-y-1/2 items-center
            justify-center rounded-full border border-line bg-surface text-ink shadow-md transition
            hover:border-gold hover:text-gold-text sm:flex"
          :aria-label="'اسلاید بعدی'"
          @click="page(1)"
        >
          <ChevronLeft :size="20" aria-hidden="true" />
        </button>
      </template>
    </div>
  </section>
</template>
