<script setup lang="ts">
import { ClipboardList, LogOut, Store } from 'lucide-vue-next'

// Field-agent portal chrome: a slim top bar (this is a phone-first work tool,
// not the admin panel) + content container.
const auth = useAdminAuth()
const route = useRoute()

const TABS = [
  { to: '/agent', label: 'کاسبان من', icon: Store },
  { to: '/agent/orders', label: 'سفارش‌ها', icon: ClipboardList },
]
function isActive(to: string) {
  return to === '/agent' ? route.path === '/agent' : route.path.startsWith(to)
}
</script>

<template>
  <div class="min-h-dvh bg-surface text-ink" data-theme="light">
    <header class="sticky top-0 z-30 border-b border-line bg-navy text-cream">
      <div class="mx-auto flex max-w-3xl items-center gap-4 px-4 py-3">
        <BrandLogo :height="22" color="#F7F3EE" />
        <span class="border-s border-white/15 ps-3 text-sm text-cream/70">پنل ایجنت</span>
        <nav class="ms-auto flex items-center gap-1" aria-label="ایجنت">
          <NuxtLink
            v-for="t in TABS"
            :key="t.to"
            :to="t.to"
            class="flex h-10 items-center gap-1.5 px-3 text-sm transition"
            :class="isActive(t.to) ? 'bg-white/10 text-cream' : 'text-cream/70 hover:text-cream'"
            :aria-current="isActive(t.to) ? 'page' : undefined"
          >
            <component :is="t.icon" :size="16" aria-hidden="true" />
            <span class="hidden sm:inline">{{ t.label }}</span>
          </NuxtLink>
          <button
            type="button"
            class="flex h-10 w-10 items-center justify-center text-cream/70 hover:text-danger-bright"
            aria-label="خروج"
            @click="auth.logout()"
          >
            <LogOut :size="18" />
          </button>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-3xl p-4 pb-16 sm:p-6">
      <slot />
    </main>
  </div>
</template>
