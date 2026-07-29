<script setup lang="ts">
import { BadgeCheck, FileCheck, RefreshCw } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'

// Icons align 1:1 with CONTENT.trust (authenticity · warranty · buyback).
// Lucide, single stroke width, decorative (aria-hidden) — the title+sub
// carries the meaning for screen readers.
const icons = [BadgeCheck, FileCheck, RefreshCw]
</script>

<template>
  <section class="border-y border-line bg-surface py-16 sm:py-20" aria-label="اعتماد و سابقه">
    <div class="mx-auto max-w-content px-6 sm:px-10">
      <ul class="grid grid-cols-1 gap-4 sm:grid-cols-3 sm:gap-6">
        <li
          v-for="(item, i) in CONTENT.trust"
          :key="i"
          class="corner-soft group flex min-h-[200px] flex-col items-center justify-center
            gap-4 border border-line bg-surface-raised px-6 py-8 text-center shadow-luxury
            transition duration-300 hover:-translate-y-1"
        >
          <!-- Circular chip: gold-soft outline → inverts to navy on hover -->
          <span
            class="flex h-16 w-16 items-center justify-center rounded-full border
              border-gold-soft bg-cream-bright text-gold-text transition-colors duration-300
              group-hover:border-navy group-hover:bg-navy group-hover:text-cream"
            aria-hidden="true"
          >
            <component :is="icons[i]" :size="26" :stroke-width="1.5" />
          </span>

          <!-- Title is the hero -->
          <span class="text-2xl font-medium leading-snug text-gold-text sm:text-3xl">
            {{ item.title }}
          </span>

          <!-- Signature gold hairline between title and sub -->
          <span class="h-px w-8 bg-gold/60" aria-hidden="true" />

          <span class="text-sm leading-6 text-ink-muted sm:text-base">{{ item.sub }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
