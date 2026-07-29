<script setup lang="ts">
// Vue port of the "tubelight-navbar" (originally React + framer-motion).
// The sliding "lamp" is a single absolutely-positioned element moved to the
// active item via CSS transform — measured from the DOM, so no motion library.
// The cart is a first-class, height-matched button on the leading edge (it also
// carries id="cart-bubble", the fly-to-cart target) so it reads as ONE control
// instead of a separate floating bubble colliding with the pill.
import { HelpCircle, Home, MessageCircle, Package, ShoppingBag } from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { CONTENT } from '~/constants/content'
import { toFa } from '~/utils/format'

defineEmits<{ cart: [] }>()

const items = [
  { name: 'خانه', url: '#top', icon: Home },
  { name: CONTENT.products.title, url: '#products', icon: Package },
  { name: CONTENT.faq.title, url: '#faq', icon: HelpCircle },
  { name: 'تماس', url: '#footer', icon: MessageCircle },
]

const route = useRoute()
const cart = useCartStore()
const { y } = import.meta.client ? useWindowScroll() : { y: ref(0) }

// Dark, translucent chrome + light text while floating over the navy hero;
// light chrome + navy text once scrolled past it (mirrors the main NavBar).
const overHero = computed(() => route.path.startsWith('/l') && y.value < 320)

const active = ref(0)
const links = ref<HTMLElement[]>([])
const lamp = ref({ transform: 'translateX(0)', width: '0px' })
const cartBtn = ref<HTMLElement | null>(null)

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

// Pulse the cart on count increase (momentum feel; reduced-motion honored by OS).
watch(
  () => cart.itemCount,
  (n, prev) => {
    if (import.meta.server || n <= prev || !cartBtn.value) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    cartBtn.value.animate(
      [{ transform: 'scale(0.9)' }, { transform: 'scale(1.08)' }, { transform: 'scale(1)' }],
      { duration: 320, easing: 'cubic-bezier(0.2,0,0,1)' },
    )
  },
)

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
  <div
    class="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-20 sm:pt-6"
  >
    <div
      class="relative flex items-center gap-1 rounded-full border p-1.5
        shadow-[0_10px_40px_-12px_rgba(4,30,66,0.45)] backdrop-blur-xl backdrop-saturate-150
        transition-colors duration-300"
      :class="overHero ? 'border-white/15 bg-navy-deep/40' : 'border-line bg-surface'"
    >
      <!-- Cart: leading (rightmost in RTL), height-matched, one with the pill.
           Keeps id="cart-bubble" so flyToCart still targets it. -->
      <button
        id="cart-bubble"
        ref="cartBtn"
        type="button"
        class="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full
          bg-navy text-cream transition-colors duration-300 hover:bg-gold"
        :aria-label="`سبد سفارش، ${toFa(cart.itemCount)} کالا`"
        @click="$emit('cart')"
      >
        <ShoppingBag :size="20" />
        <span
          v-if="cart.itemCount"
          class="tnum absolute -end-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center
            rounded-full bg-gold px-1 text-[11px] font-bold text-white"
        >
          {{ toFa(cart.itemCount) }}
        </span>
      </button>

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
