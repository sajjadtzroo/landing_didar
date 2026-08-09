<script setup lang="ts">
import {
  BadgeCheck,
  BarChart3,
  Coins,
  LayoutGrid,
  LayoutTemplate,
  LogOut,
  Package,
  ScrollText,
  ShieldCheck,
  ShoppingCart,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { toFa } from '~/utils/format'

// Shared sidebar body — used by both the fixed desktop rail and the mobile
// drawer. Emits `navigate` so the drawer can close on selection.
defineEmits<{ navigate: [] }>()

const auth = useAdminAuth()
const route = useRoute()

// Grouped navigation: labelled sections give hierarchy as the panel grows.
const groups = [
  {
    label: 'نمای کلی',
    items: [
      { to: '/admin', label: 'داشبورد', icon: BarChart3 },
      { to: '/admin/orders', label: 'سفارش‌ها', icon: ShoppingCart, badge: true },
      { to: '/admin/prices', label: 'قیمت طلا', icon: Coins },
    ],
  },
  {
    label: 'کاتالوگ',
    items: [
      { to: '/admin/products', label: 'محصولات', icon: Package },
      { to: '/admin/serials', label: 'سریال‌ها / اصالت', icon: BadgeCheck },
      { to: '/admin/portfolios', label: 'پورتفولیوها', icon: LayoutGrid },
      { to: '/admin/landings', label: 'صفحات فرود', icon: LayoutTemplate },
      { to: '/admin/faqs', label: 'سؤالات متداول', icon: ScrollText },
    ],
  },
  {
    label: 'مشتریان',
    items: [{ to: '/admin/customers', label: 'احراز هویت مشتریان', icon: ShieldCheck }],
  },
]

// Exact match for the dashboard, prefix match for sections.
function isActive(to: string) {
  return to === '/admin' ? route.path === '/admin' : route.path.startsWith(to)
}

const initial = computed(() => (auth.username || 'مدیر').trim().charAt(0))
</script>

<template>
  <div class="flex h-full flex-col bg-navy text-cream">
    <!-- Brand -->
    <div class="flex items-center gap-3 border-b border-white/10 px-5 py-5">
      <BrandLogo :height="24" color="#F7F3EE" />
      <span class="text-xs text-cream/50">مدیریت</span>
    </div>

    <!-- Primary nav (grouped) -->
    <nav class="flex-1 overflow-y-auto py-3" aria-label="منوی مدیریت">
      <div v-for="group in groups" :key="group.label" class="mb-2">
        <p class="px-5 pb-1.5 pt-4 text-[11px] tracking-wide text-cream/40">
          {{ group.label }}
        </p>
        <NuxtLink
          v-for="item in group.items"
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
      </div>
    </nav>

    <!-- Admin identity + logout (destructive-nav-separation) -->
    <div class="border-t border-white/10 p-3">
      <div class="mb-1 flex items-center gap-3 px-4 py-2">
        <span
          class="flex h-9 w-9 shrink-0 items-center justify-center bg-white/10 text-sm
            font-medium text-cream"
          aria-hidden="true"
        >
          {{ initial }}
        </span>
        <span class="truncate text-sm text-cream/80">{{ auth.username || 'مدیر' }}</span>
      </div>
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
