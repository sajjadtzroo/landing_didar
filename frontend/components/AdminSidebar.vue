<script setup lang="ts">
import {
  BarChart3,
  LayoutGrid,
  LayoutTemplate,
  LogOut,
  Package,
  ScrollText,
  ShoppingCart,
} from 'lucide-vue-next'
import { toFa } from '~/utils/format'

// Shared sidebar body — used by both the fixed desktop rail and the mobile
// drawer. Emits `navigate` so the drawer can close on selection.
defineEmits<{ navigate: [] }>()

const auth = useAdminAuth()
const route = useRoute()
const nav = [
  { to: '/admin', label: 'داشبورد', icon: BarChart3 },
  { to: '/admin/orders', label: 'سفارش‌ها', icon: ShoppingCart, badge: true },
  { to: '/admin/products', label: 'محصولات', icon: Package },
  { to: '/admin/portfolios', label: 'پورتفولیوها', icon: LayoutGrid },
  { to: '/admin/landings', label: 'صفحات فرود', icon: LayoutTemplate },
  { to: '/admin/faqs', label: 'سؤالات متداول', icon: ScrollText },
]

// Exact match for the dashboard, prefix match for sections.
function isActive(to: string) {
  return to === '/admin' ? route.path === '/admin' : route.path.startsWith(to)
}
</script>

<template>
  <div class="flex h-full flex-col bg-navy text-cream">
    <!-- Brand -->
    <div class="flex items-center gap-3 border-b border-white/10 px-5 py-5">
      <BrandLogo :height="24" color="#F7F3EE" />
      <span class="text-xs text-cream/50">مدیریت</span>
    </div>

    <!-- Primary nav -->
    <nav class="flex-1 space-y-1 overflow-y-auto p-3" aria-label="منوی مدیریت">
      <NuxtLink
        v-for="item in nav"
        :key="item.to"
        :to="item.to"
        class="flex min-h-11 items-center gap-3 border-s-[3px] px-4 text-sm transition-colors
          duration-200"
        :class="
          isActive(item.to)
            ? 'border-gold bg-white/10 text-cream'
            : 'border-transparent text-cream/70 hover:bg-white/5 hover:text-cream'
        "
        :aria-current="isActive(item.to) ? 'page' : undefined"
        @click="$emit('navigate')"
      >
        <component :is="item.icon" :size="20" :stroke-width="1.75" />
        <span>{{ item.label }}</span>
        <span
          v-if="item.badge && auth.unread"
          class="tnum ms-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-gold
            px-1 text-[11px] font-bold text-white"
          :aria-label="`${toFa(auth.unread)} خوانده‌نشده`"
        >
          {{ toFa(auth.unread) }}
        </span>
      </NuxtLink>
    </nav>

    <!-- Logout — separated from navigation (destructive-nav-separation) -->
    <div class="border-t border-white/10 p-3">
      <button
        type="button"
        class="flex min-h-11 w-full items-center gap-3 px-4 text-sm text-cream/70
          transition-colors hover:bg-white/5 hover:text-danger-bright"
        @click="auth.logout()"
      >
        <LogOut :size="20" :stroke-width="1.75" /> خروج
      </button>
    </div>
  </div>
</template>
