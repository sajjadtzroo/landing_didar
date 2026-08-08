<script setup lang="ts">
import { Heart, Home, ShoppingBag, ShoppingCart, User } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

// Mobile-only bottom tab bar for storefront pages (hidden ≥sm; landings use the
// tubelight pill instead). Cart is an action (opens the drawer), the rest route.
const route = useRoute()
const cart = useCartStore()
const favorites = useFavoritesStore()
const { openCart } = useUiState()

const isActive = (to: string) =>
  to === '/' ? route.path === '/' : route.path.startsWith(to)
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-40 flex items-stretch border-t border-line
      bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl sm:hidden"
    aria-label="ناوبری اصلی"
  >
    <NuxtLink
      to="/shop"
      class="flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] transition"
      :class="isActive('/shop') ? 'text-gold-text' : 'text-ink-muted'"
      :aria-current="isActive('/shop') ? 'page' : undefined"
    >
      <ShoppingBag :size="22" aria-hidden="true" />
      {{ CONTENT.nav.shop }}
    </NuxtLink>

    <NuxtLink
      to="/"
      class="flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] transition"
      :class="route.path === '/' ? 'text-gold-text' : 'text-ink-muted'"
    >
      <Home :size="22" aria-hidden="true" />
      {{ CONTENT.nav.home }}
    </NuxtLink>

    <!-- Cart: opens the drawer (not a route) -->
    <button
      type="button"
      class="relative flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px]
        text-ink-muted transition"
      @click="openCart"
    >
      <span class="relative">
        <ShoppingCart :size="22" aria-hidden="true" />
        <span
          v-if="cart.itemCount"
          class="tnum absolute -end-2 -top-1.5 flex h-4 min-w-4 items-center justify-center
            rounded-full bg-gold px-1 text-[10px] font-bold text-navy-deep"
        >{{ toFa(cart.itemCount) }}</span>
      </span>
      {{ CONTENT.nav.cart }}
    </button>

    <NuxtLink
      to="/account/favorites"
      class="relative flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] transition"
      :class="isActive('/account/favorites') ? 'text-gold-text' : 'text-ink-muted'"
    >
      <span class="relative">
        <Heart :size="22" aria-hidden="true" />
        <span
          v-if="favorites.count"
          class="tnum absolute -end-2 -top-1.5 flex h-4 min-w-4 items-center justify-center
            rounded-full bg-gold px-1 text-[10px] font-bold text-navy-deep"
        >{{ toFa(favorites.count) }}</span>
      </span>
      {{ CONTENT.nav.favorites }}
    </NuxtLink>

    <NuxtLink
      to="/account"
      class="flex flex-1 flex-col items-center justify-center gap-1 py-2 text-[11px] transition"
      :class="route.path === '/account' ? 'text-gold-text' : 'text-ink-muted'"
    >
      <User :size="22" aria-hidden="true" />
      {{ CONTENT.nav.accountShort }}
    </NuxtLink>
  </nav>
</template>
