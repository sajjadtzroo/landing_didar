<script setup lang="ts">
import { ChevronDown, Heart, ShoppingBag, User } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Portfolio } from '~/types'
import { toFa } from '~/utils/format'

defineEmits<{ order: [] }>()

const { open: promoOpen } = usePromo()

const cart = useCartStore()
const favorites = useFavoritesStore()
const { openCart } = useUiState()

// Section link: gold text + a gold underline that grows on hover, locked open
// on the active route (nav-state-active).
const linkClass =
  'relative text-[15px] tracking-wide transition hover:text-gold-text after:absolute ' +
  'after:inset-x-0 after:-bottom-1.5 after:h-px after:origin-center after:scale-x-0 ' +
  'after:bg-gold after:transition-transform after:duration-300 hover:after:scale-x-100'
const linkActive = 'text-gold-text after:scale-x-100'

// Curated collections menu — reuses the /shop portfolios payload (shared key, so
// Nuxt dedupes it; cached 60s server-side). ponytail: add a lightweight
// /portfolios/menu endpoint only if this payload grows heavy.
const { data: portfolios } = useFetch<Portfolio[]>('/portfolios', {
  baseURL: useApiBase(),
  key: 'portfolios',
})
const collections = computed(() => portfolios.value || [])
</script>

<template>
  <!-- Cream boutique bar (reference: logo right, links centered, actions left).
       --header keeps it theme-aware: warm cream in light, navy in dark. -->
  <header
    class="chrome-blur fixed inset-x-0 z-40 hidden border-b border-line/60 bg-header
      text-ink backdrop-blur-xl backdrop-saturate-150 transition-[top] duration-300 sm:block"
    :class="promoOpen ? 'top-20 sm:top-14' : 'top-0'"
  >
    <nav
      class="mx-auto grid max-w-hero grid-cols-[1fr_auto_1fr] items-center px-5 py-4 sm:px-10"
      aria-label="اصلی"
    >
      <!-- Brand (start = right in RTL) -->
      <NuxtLink
        to="/"
        class="justify-self-start"
        :aria-label="`${CONTENT.brand} — خانه`"
      >
        <BrandLogo :height="30" />
      </NuxtLink>

      <!-- Section links, centered -->
      <div class="hidden items-center gap-8 sm:flex">
        <NuxtLink to="/l/one" :class="linkClass" :active-class="linkActive">
          {{ CONTENT.nav.home }}
        </NuxtLink>

        <NuxtLink to="/shop" :class="linkClass" :active-class="linkActive">
          {{ CONTENT.nav.shop }}
        </NuxtLink>

        <!-- Collections dropdown (hover/focus). Hidden when there are none. -->
        <div v-if="collections.length" class="group relative">
          <button
            type="button"
            class="flex items-center gap-1.5 text-[15px] tracking-wide transition
              hover:text-gold-text group-focus-within:text-gold-text"
            aria-haspopup="true"
          >
            {{ CONTENT.nav.collections }}
            <ChevronDown
              :size="14"
              class="transition-transform duration-300 group-hover:rotate-180"
              aria-hidden="true"
            />
          </button>
          <div
            class="invisible absolute end-0 top-full z-50 min-w-48 border border-line bg-surface/95
              py-2 opacity-0 shadow-lg backdrop-blur-xl transition
              group-hover:visible group-hover:opacity-100
              group-focus-within:visible group-focus-within:opacity-100"
          >
            <NuxtLink
              v-for="pf in collections"
              :key="pf.slug"
              :to="`/shop/${pf.slug}`"
              class="block px-4 py-2 text-sm text-ink transition hover:bg-surface-raised hover:text-gold-text"
              active-class="text-gold-text"
            >
              {{ pf.name }}
            </NuxtLink>
          </div>
        </div>

        <NuxtLink to="/verify" :class="linkClass" :active-class="linkActive">
          {{ CONTENT.nav.verify }}
        </NuxtLink>

        <NuxtLink to="/account" :class="linkClass" :active-class="linkActive">
          {{ CONTENT.nav.account }}
        </NuxtLink>
      </div>

      <!-- Actions (end = left in RTL): heart, bag, then the navy order block -->
      <div class="flex items-center gap-1 justify-self-end sm:gap-3">
        <NuxtLink
          to="/account"
          class="flex h-11 w-11 items-center justify-center transition hover:text-gold-text sm:hidden"
          :aria-label="CONTENT.nav.account"
        >
          <User :size="20" aria-hidden="true" />
        </NuxtLink>
        <NuxtLink
          to="/account/favorites"
          class="relative hidden h-11 w-11 items-center justify-center transition
            hover:text-gold-text sm:flex"
          :aria-label="CONTENT.nav.favorites"
        >
          <Heart :size="21" aria-hidden="true" />
          <span
            v-if="favorites.count"
            class="tnum absolute -top-1 end-0 flex h-5 min-w-5 items-center justify-center
              rounded-full bg-gold px-1 text-[11px] font-bold text-navy-deep
              ring-2 ring-header"
          >
            {{ toFa(favorites.count) }}
          </span>
        </NuxtLink>
        <button
          type="button"
          class="relative flex h-11 w-11 items-center justify-center transition hover:text-gold-text"
          :aria-label="CONTENT.cart.title"
          @click="openCart"
        >
          <ShoppingBag :size="21" aria-hidden="true" />
          <span
            v-if="cart.itemCount"
            class="tnum absolute -top-1 end-0 flex h-5 min-w-5 items-center justify-center
              rounded-full bg-gold px-1 text-[11px] font-bold text-navy-deep
              ring-2 ring-header"
          >
            {{ toFa(cart.itemCount) }}
          </span>
        </button>
        <button
          type="button"
          class="ms-1 flex h-12 items-center justify-center bg-navy px-8 text-[15px]
            font-medium text-white transition duration-300 hover:bg-gold hover:text-navy-deep"
          @click="$emit('order')"
        >
          {{ CONTENT.nav.order }}
        </button>
      </div>
    </nav>
  </header>
</template>
