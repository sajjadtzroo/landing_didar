<script setup lang="ts">
import { Menu } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

// RTL admin shell: fixed sidebar on the leading (right) edge ≥lg; a slide-in
// drawer with a hamburger below that. Content is padded to clear the rail.
const open = ref(false)
const route = useRoute()
watch(() => route.path, () => (open.value = false)) // close drawer on navigate

// Current-section label for the mobile top bar (desktop shows the full rail).
const SECTIONS: [string, string][] = [
  ['/admin/orders', 'سفارش‌ها'],
  ['/admin/prices', 'قیمت طلا'],
  ['/admin/products', 'محصولات'],
  ['/admin/serials', 'سریال‌ها / اصالت'],
  ['/admin/portfolios', 'پورتفولیوها'],
  ['/admin/landings', 'صفحات فرود'],
  ['/admin/faqs', 'سؤالات متداول'],
  ['/admin/customers', 'احراز هویت مشتریان'],
  ['/admin/users', 'کاربران'],
  ['/admin/audit', 'گزارش فعالیت'],
]
const pageTitle = computed(
  () => SECTIONS.find(([p]) => route.path.startsWith(p))?.[1] ?? 'داشبورد',
)
if (import.meta.client) {
  useEventListener(window, 'keydown', (e) => {
    if (e.key === 'Escape') open.value = false
  })
}
</script>

<template>
  <div class="relative min-h-dvh bg-surface text-ink" data-theme="light">
    <!-- Ambient aura: brand-tinted glows the glass cards refract. Painted first
         → sits above the base surface, below the sidebar/content. -->
    <div class="admin-aura" aria-hidden="true">
      <span class="-start-24 -top-32 h-96 w-96 bg-gold/25 blur-[120px]" />
      <span class="-end-24 top-1/3 h-80 w-80 bg-navy/15 blur-[120px]" />
      <span class="bottom-0 start-1/3 h-72 w-72 bg-gold-soft/20 blur-[110px]" />
    </div>

    <!-- Fixed sidebar — RTL leading (right) edge -->
    <aside class="fixed inset-y-0 start-0 z-30 hidden w-64 shadow-luxury lg:block">
      <AdminSidebar />
    </aside>

    <!-- Content (padded to clear the sidebar on its side) -->
    <div class="lg:ps-64">
      <!-- Mobile top bar with hamburger -->
      <header
        class="chrome-blur sticky top-0 z-20 flex items-center gap-3 border-b border-line
          bg-surface/90 px-4 py-3 backdrop-blur lg:hidden"
      >
        <button
          type="button"
          class="flex h-11 w-11 items-center justify-center text-ink hover:text-gold-text"
          aria-label="باز کردن منو"
          @click="open = true"
        >
          <Menu :size="24" />
        </button>
        <BrandLogo :height="22" color="#835F26" />
        <span class="ms-1 border-s border-line ps-3 text-sm font-medium text-ink">
          {{ pageTitle }}
        </span>
      </header>

      <main class="mx-auto max-w-content p-4 sm:p-6">
        <slot />
      </main>
    </div>

    <!-- Mobile drawer -->
    <Transition name="drawer">
      <div v-if="open" class="fixed inset-0 z-40 lg:hidden">
        <div class="absolute inset-0 bg-navy-deep/60" @click="open = false" aria-hidden="true" />
        <aside class="drawer-panel absolute inset-y-0 start-0 w-72 shadow-luxury">
          <AdminSidebar @navigate="open = false" />
        </aside>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.25s ease;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 0.25s cubic-bezier(0.2, 0, 0, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
/* Slide from the leading (right) edge in RTL. */
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}
@media (prefers-reduced-motion: reduce) {
  .drawer-enter-from .drawer-panel,
  .drawer-leave-to .drawer-panel {
    transform: none;
  }
}
</style>
