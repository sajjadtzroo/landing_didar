<script setup lang="ts">
// پرفروش‌ترین‌ها as a ranked "chart", not another product carousel: navy panel
// (the footer's premium language), rank #1 featured with a display numeral,
// ranks ۲–۵ as compact list rows. Data is real units sold (order_items).
import { ChevronLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'
import { formatGramsCompact, toFa } from '~/utils/format'

const props = defineProps<{ products: Product[] }>()

const top = computed(() => props.products[0])
const runners = computed(() => props.products.slice(1, 5))
</script>

<template>
  <section
    v-if="top"
    class="mb-16 bg-navy text-cream"
    :aria-label="CONTENT.shop.bestSellersTitle"
  >
    <div class="px-5 py-10 sm:px-10 sm:py-14">
      <!-- Header: gold hairline + eyebrow, cream title (footer's visual language) -->
      <p class="text-xs tracking-[0.3em] text-gold-soft">
        {{ CONTENT.shop.bestSellersEyebrow }}
      </p>
      <h2 class="mt-2 border-b border-gold/20 pb-6 text-2xl font-medium sm:text-3xl">
        {{ CONTENT.shop.bestSellersTitle }}
      </h2>

      <div class="mt-8 grid gap-10 lg:grid-cols-2 lg:gap-14">
        <!-- Rank #1: featured -->
        <NuxtLink
          :to="`/products/${top.slug}`"
          class="group relative block"
        >
          <div class="relative aspect-[4/3] overflow-hidden bg-navy-deep">
            <img
              v-if="top.image_url"
              :src="top.image_url"
              :alt="top.name"
              loading="lazy"
              class="h-full w-full object-contain transition-transform duration-300 group-hover:scale-[1.03]"
            />
            <!-- Display numeral: the "chart" signal -->
            <span
              class="tnum absolute -top-2 end-3 text-7xl font-bold leading-none text-gold-soft/90 drop-shadow sm:text-8xl"
              aria-hidden="true"
            >
              {{ toFa(1) }}
            </span>
          </div>
          <div class="mt-4 flex items-baseline justify-between gap-4">
            <span class="text-lg font-medium transition-colors group-hover:text-gold-soft">
              {{ top.name }}
            </span>
            <span v-if="top.weight_grams" class="tnum shrink-0 text-sm text-cream/70">
              {{ formatGramsCompact(top.weight_grams) }}
            </span>
          </div>
        </NuxtLink>

        <!-- Ranks ۲–۵: compact chart rows -->
        <ol class="divide-y divide-gold/15">
          <li v-for="(p, i) in runners" :key="p.id">
            <NuxtLink
              :to="`/products/${p.slug}`"
              class="group flex min-h-[72px] items-center gap-4 py-3 transition-colors duration-200 hover:bg-white/5 sm:gap-5"
            >
              <span
                class="tnum w-8 shrink-0 text-center text-3xl font-bold text-gold-soft/70"
                aria-hidden="true"
              >
                {{ toFa(i + 2) }}
              </span>
              <img
                v-if="p.image_url"
                :src="p.image_url"
                :alt="''"
                loading="lazy"
                class="h-14 w-14 shrink-0 object-cover"
              />
              <div v-else class="h-14 w-14 shrink-0 bg-navy-deep" aria-hidden="true" />
              <div class="min-w-0 flex-1">
                <p class="truncate font-medium transition-colors group-hover:text-gold-soft">
                  {{ p.name }}
                </p>
                <p v-if="p.weight_grams" class="tnum mt-0.5 text-sm text-cream/60">
                  {{ formatGramsCompact(p.weight_grams) }}
                </p>
              </div>
              <ChevronLeft
                :size="18"
                class="shrink-0 text-cream/40 transition-colors group-hover:text-gold-soft"
                aria-hidden="true"
              />
            </NuxtLink>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>
