<script setup lang="ts">
import { LayoutDashboard, LogOut, Heart, MapPin, ShoppingBag, ShieldCheck } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'

const { customer, logout } = useCustomerAuth()

const TABS = [
  { to: '/account', label: CONTENT.account.tabs.overview, icon: LayoutDashboard },
  { to: '/account/orders', label: CONTENT.account.tabs.orders, icon: ShoppingBag },
  { to: '/account/favorites', label: CONTENT.account.tabs.favorites, icon: Heart },
  { to: '/account/profile', label: CONTENT.account.tabs.profile, icon: MapPin },
  { to: '/account/verification', label: 'احراز هویت', icon: ShieldCheck },
]

async function onLogout() {
  await logout()
  await navigateTo('/account/login')
}
</script>

<template>
  <main class="pt-32 sm:pt-28">
    <div class="mx-auto max-w-content px-5 pb-20 sm:px-10">
      <div class="mb-6 flex items-center justify-between">
        <h1 class="text-2xl font-medium text-ink sm:text-3xl">{{ CONTENT.account.panelTitle }}</h1>
        <button
          type="button"
          class="flex items-center gap-2 text-sm text-ink-muted transition hover:text-danger"
          @click="onLogout"
        >
          <LogOut :size="16" /> {{ CONTENT.account.logout }}
        </button>
      </div>

      <div class="grid gap-6 lg:grid-cols-[220px_1fr]">
        <!-- Sidebar (desktop) / top tabs (mobile) -->
        <nav class="flex gap-2 overflow-x-auto border-b border-line pb-2 lg:flex-col lg:border-b-0 lg:pb-0">
          <NuxtLink
            v-for="t in TABS"
            :key="t.to"
            :to="t.to"
            class="flex shrink-0 items-center gap-2 px-3 py-2 text-sm text-ink-muted transition hover:text-ink"
            exact-active-class="!bg-navy !text-white"
          >
            <component :is="t.icon" :size="16" aria-hidden="true" />
            {{ t.label }}
          </NuxtLink>
        </nav>

        <section>
          <slot :customer="customer" />
        </section>
      </div>
    </div>
  </main>
</template>
