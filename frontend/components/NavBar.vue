<script setup lang="ts">
import { ShoppingBag, User } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

defineEmits<{ order: [] }>()

const route = useRoute()
const { open: promoOpen } = usePromo()
const { y } = import.meta.client ? useWindowScroll() : { y: ref(0) }

const cart = useCartStore()
const { openCart } = useUiState()

const LINKS = [
  { to: '/shop', label: CONTENT.nav.shop },
  { to: '/account', label: CONTENT.nav.account },
]

// Transparent (light text) only while sitting over the dark hero on a landing
// page; frosted glass (dark text) after scrolling, and on every inner page.
const onLanding = computed(() => route.path === '/' || route.path.startsWith('/l/'))
const overHero = computed(() => onLanding.value && y.value < 80)
</script>

<template>
  <header
    class="chrome-blur fixed inset-x-0 z-40 transition-[colors,top] duration-300"
    :class="[
      overHero
        ? 'bg-transparent text-cream'
        : 'border-b border-line bg-surface/70 text-ink backdrop-blur-xl backdrop-saturate-150',
      promoOpen ? 'top-20 sm:top-14' : 'top-0',
    ]"
  >
    <!-- Legibility scrim over the hero (only in the transparent state) -->
    <div
      v-if="overHero"
      class="pointer-events-none absolute inset-0 bg-gradient-to-b from-navy-deep/50 to-transparent"
      aria-hidden="true"
    />

    <nav
      class="relative mx-auto flex max-w-content items-center justify-between px-5 py-3 sm:px-10"
      aria-label="اصلی"
    >
      <!-- Brand -->
      <NuxtLink to="/" class="flex items-center" :aria-label="`${CONTENT.brand} — خانه`">
        <BrandLogo :height="26" />
      </NuxtLink>

      <!-- Section links -->
      <div class="hidden items-center gap-6 sm:flex">
        <NuxtLink
          v-for="l in LINKS"
          :key="l.to"
          :to="l.to"
          class="text-sm transition hover:text-gold-text"
          active-class="text-gold-text"
        >
          {{ l.label }}
        </NuxtLink>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-2 sm:gap-4">
        <NuxtLink
          to="/account"
          class="flex h-11 w-11 items-center justify-center transition hover:text-gold-text sm:hidden"
          :aria-label="CONTENT.nav.account"
        >
          <User :size="20" aria-hidden="true" />
        </NuxtLink>
        <button
          type="button"
          class="relative flex h-11 w-11 items-center justify-center transition hover:text-gold-text"
          :aria-label="CONTENT.cart.title"
          @click="openCart"
        >
          <ShoppingBag :size="20" aria-hidden="true" />
          <span
            v-if="cart.itemCount"
            class="tnum absolute -end-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center
              rounded-full bg-gold px-1 text-[11px] font-bold text-navy-deep"
          >
            {{ toFa(cart.itemCount) }}
          </span>
        </button>
        <button
          type="button"
          class="flex h-11 items-center justify-center bg-navy px-5 text-sm font-medium
            text-white transition duration-300 hover:bg-gold"
          @click="$emit('order')"
        >
          {{ CONTENT.nav.order }}
        </button>
      </div>
    </nav>
  </header>
</template>
