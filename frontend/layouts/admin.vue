<script setup lang="ts">
import { BarChart3, LogOut, Package, ScrollText, ShoppingCart } from 'lucide-vue-next'
import { toFa } from '~/utils/format'

const auth = useAdminAuth()
const nav = [
  { to: '/admin', label: 'داشبورد', icon: BarChart3 },
  { to: '/admin/orders', label: 'سفارش‌ها', icon: ShoppingCart, badge: true },
  { to: '/admin/products', label: 'محصولات', icon: Package },
  { to: '/admin/faqs', label: 'سؤالات متداول', icon: ScrollText },
]
</script>

<template>
  <div class="min-h-dvh bg-surface text-ink" data-theme="light">
    <div class="mx-auto flex max-w-content flex-col gap-6 px-4 py-6 md:flex-row md:px-6">
      <!-- Sidebar (drawer on mobile is out of scope; collapses to top row) -->
      <aside class="shrink-0 md:w-56">
        <p class="mb-4 px-2 text-lg font-medium">دیدار گلد — مدیریت</p>
        <nav class="flex gap-1 overflow-x-auto md:flex-col">
          <NuxtLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-2 whitespace-nowrap px-3 py-2 text-sm text-ink-muted
              hover:text-ink"
            active-class="border-e-2 border-gold bg-surface-raised text-ink"
          >
            <component :is="item.icon" :size="18" />
            {{ item.label }}
            <span
              v-if="item.badge && auth.unread"
              class="tnum ms-auto flex h-5 min-w-5 items-center justify-center rounded-full
                bg-gold px-1 text-xs text-white"
            >
              {{ toFa(auth.unread) }}
            </span>
          </NuxtLink>
          <button
            class="mt-2 flex items-center gap-2 px-3 py-2 text-sm text-ink-muted hover:text-danger"
            @click="auth.logout()"
          >
            <LogOut :size="18" /> خروج
          </button>
        </nav>
      </aside>

      <main class="min-w-0 flex-1">
        <slot />
      </main>
    </div>
  </div>
</template>
