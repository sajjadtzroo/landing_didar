<script setup lang="ts">
// Trust strip for /shop — surfaces the authenticity/warranty/buyback machinery
// that already exists (serials + /verify + warranty module) as buyer confidence.
import { Banknote, BadgeCheck, ShieldCheck } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'
</script>

<template>
  <section class="mb-10 grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-5" aria-label="اعتماد">
    <!-- Authenticity — the only actionable one: links to the DGV verify page -->
    <NuxtLink
      to="/verify"
      class="group flex items-center gap-3 border border-line bg-surface-raised p-4 transition
        hover:border-gold"
    >
      <BadgeCheck :size="26" class="shrink-0 text-gold-text" aria-hidden="true" />
      <span class="min-w-0">
        <span class="block text-sm font-medium text-ink">{{ CONTENT.shop.trustVerify }}</span>
        <span class="block text-xs text-gold-text underline-offset-2 group-hover:underline">
          {{ CONTENT.shop.trustVerifyCta }}
        </span>
      </span>
    </NuxtLink>

    <div class="flex items-center gap-3 border border-line bg-surface-raised p-4">
      <ShieldCheck :size="26" class="shrink-0 text-gold-text" aria-hidden="true" />
      <span class="text-sm font-medium text-ink">{{ CONTENT.shop.trustWarranty }}</span>
    </div>

    <div class="flex items-center gap-3 border border-line bg-surface-raised p-4">
      <Banknote :size="26" class="shrink-0 text-gold-text" aria-hidden="true" />
      <span class="text-sm font-medium text-ink">{{ CONTENT.shop.trustBuyback }}</span>
    </div>
  </section>
</template>
