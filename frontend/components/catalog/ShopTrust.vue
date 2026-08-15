<script setup lang="ts">
// Trust strip for /shop — surfaces the authenticity/warranty/buyback machinery
// that already exists (serials + /verify + warranty module) as buyer confidence.
import { Banknote, BadgeCheck, ShieldCheck } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'
</script>

<template>
  <!-- Mobile: one compact 3-up row (icon over label) so trust reads in a glance
       without eating a screen; desktop keeps the roomier horizontal cards. -->
  <section class="mb-6 grid grid-cols-3 gap-2 sm:mb-10 sm:gap-5" aria-label="اعتماد">
    <!-- Authenticity — the only actionable one: links to the DGV verify page -->
    <NuxtLink
      to="/verify"
      class="group flex min-h-11 flex-col items-center gap-1.5 border border-line bg-surface-raised
        p-2.5 text-center transition hover:border-gold sm:flex-row sm:gap-3 sm:p-4 sm:text-start"
    >
      <BadgeCheck class="h-5 w-5 shrink-0 text-gold-text sm:h-[26px] sm:w-[26px]" aria-hidden="true" />
      <span class="min-w-0">
        <span class="block text-[11px] font-medium leading-4 text-ink sm:text-sm sm:leading-5">
          {{ CONTENT.shop.trustVerify }}
        </span>
        <span class="hidden text-xs text-gold-text underline-offset-2 group-hover:underline sm:block">
          {{ CONTENT.shop.trustVerifyCta }}
        </span>
      </span>
    </NuxtLink>

    <div
      class="flex min-h-11 flex-col items-center gap-1.5 border border-line bg-surface-raised
        p-2.5 text-center sm:flex-row sm:gap-3 sm:p-4 sm:text-start"
    >
      <ShieldCheck class="h-5 w-5 shrink-0 text-gold-text sm:h-[26px] sm:w-[26px]" aria-hidden="true" />
      <span class="text-[11px] font-medium leading-4 text-ink sm:text-sm sm:leading-5">
        {{ CONTENT.shop.trustWarranty }}
      </span>
    </div>

    <div
      class="flex min-h-11 flex-col items-center gap-1.5 border border-line bg-surface-raised
        p-2.5 text-center sm:flex-row sm:gap-3 sm:p-4 sm:text-start"
    >
      <Banknote class="h-5 w-5 shrink-0 text-gold-text sm:h-[26px] sm:w-[26px]" aria-hidden="true" />
      <span class="text-[11px] font-medium leading-4 text-ink sm:text-sm sm:leading-5">
        {{ CONTENT.shop.trustBuyback }}
      </span>
    </div>
  </section>
</template>
