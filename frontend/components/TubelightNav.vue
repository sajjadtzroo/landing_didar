<script setup lang="ts">
// Vue port of the "tubelight-navbar" (originally React + framer-motion).
// The sliding "lamp" is a single absolutely-positioned element moved to the
// active item via CSS transform — measured from the DOM, so no motion library.
// Nav-only: cart lives in a separate top-left fab (CartFab); ordering is reached
// through the cart drawer.
import { HelpCircle, Home, MessageCircle, Package } from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { CONTENT } from '~/constants/content'

const items = [
  { name: 'خانه', url: '#top', icon: Home },
  { name: CONTENT.products.title, url: '#products', icon: Package },
  { name: CONTENT.faq.title, url: '#faq', icon: HelpCircle },
  { name: 'تماس', url: '#footer', icon: MessageCircle },
]

const route = useRoute()
const { y } = import.meta.client ? useWindowScroll() : { y: ref(0) }

// Dark, translucent chrome + light text while floating over the navy hero;
// light chrome + navy text once scrolled past it.
const overHero = computed(() => route.path.startsWith('/l') && y.value < 320)

const active = ref(0)
const links = ref<HTMLElement[]>([])
const lamp = ref({ transform: 'translateX(0)', width: '0px' })

function moveLamp() {
  const el = links.value[active.value]
  if (!el) return
  lamp.value = { transform: `translateX(${el.offsetLeft}px)`, width: `${el.offsetWidth}px` }
}

// Scroll-spy: active = furthest section whose top has passed the nav line.
function syncActive() {
  const line = y.value + 140
  let idx = 0
  items.forEach((item, i) => {
    if (item.url === '#top') return
    const el = document.querySelector(item.url) as HTMLElement | null
    if (el && el.offsetTop <= line) idx = i
  })
  active.value = idx
}

function select(i: number, url: string) {
  active.value = i
  const target = url === '#top' ? document.body : document.querySelector(url)
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  moveLamp()
  syncActive()
  window.addEventListener('resize', moveLamp)
})
onUnmounted(() => window.removeEventListener('resize', moveLamp))
watch(active, () => nextTick(moveLamp))
watch(y, syncActive)
</script>

<template>
  <!-- Top on mobile (below the main navbar) and top-center on laptop -->
  <div
    class="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-20 sm:pt-6"
  >

    <div
      class="relative flex items-center gap-1 rounded-full border p-1.5
        shadow-[0_10px_40px_-12px_rgba(4,30,66,0.45)] backdrop-blur-xl backdrop-saturate-150
        transition-colors duration-300"
      :class="overHero ? 'border-white/15 bg-navy-deep/40' : 'border-line bg-surface'"
    >
      <!-- Sliding lamp (behind the items) -->
      <span
        class="pointer-events-none absolute inset-y-1.5 left-0 z-0 rounded-full bg-gold/15
          transition-[transform,width] duration-300 ease-out"
        :style="lamp"
      >
        <span class="absolute -top-2 left-1/2 h-1 w-8 -translate-x-1/2 rounded-t-full bg-gold">
          <span class="absolute -left-2 -top-2 h-6 w-12 rounded-full bg-gold/25 blur-md" />
          <span class="absolute -top-1 h-6 w-8 rounded-full bg-gold/25 blur-md" />
          <span class="absolute left-2 top-0 h-4 w-4 rounded-full bg-gold/25 blur-sm" />
        </span>
      </span>

      <a
        v-for="(item, i) in items"
        :key="item.name"
        ref="links"
        :href="item.url"
        class="relative z-10 flex min-h-11 cursor-pointer items-center rounded-full px-4
          text-sm font-semibold transition-colors sm:px-5"
        :class="
          active === i
            ? overHero ? 'text-white' : 'text-gold-text'
            : overHero ? 'text-cream/80 hover:text-white' : 'text-ink hover:text-gold-text'
        "
        @click.prevent="select(i, item.url)"
      >
        <span class="hidden md:inline">{{ item.name }}</span>
        <component :is="item.icon" :size="18" :stroke-width="2.5" class="md:hidden" />
      </a>
    </div>
  </div>
</template>
