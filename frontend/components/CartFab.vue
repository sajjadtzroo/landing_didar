<script setup lang="ts">
// Floating cart button, pinned top-left. Holds id="cart-bubble" (fly-to-cart
// target) and pulses on count increase. Only shown where there's no top navbar
// with its own cart (i.e. the landing).
import { ShoppingBag } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { toFa } from '~/utils/format'

defineEmits<{ open: [] }>()

const cart = useCartStore()
const { open: promoOpen } = usePromo()
const btn = ref<HTMLElement | null>(null)

watch(
  () => cart.itemCount,
  (n, prev) => {
    if (import.meta.server || n <= prev || !btn.value) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    btn.value.animate(
      [{ transform: 'scale(0.9)' }, { transform: 'scale(1.08)' }, { transform: 'scale(1)' }],
      { duration: 320, easing: 'cubic-bezier(0.2,0,0,1)' },
    )
  },
)
</script>

<template>
  <button
    id="cart-bubble"
    ref="btn"
    type="button"
    class="fixed left-4 z-50 flex h-14 w-14 items-center justify-center rounded-full
      bg-navy text-cream shadow-[0_10px_40px_-12px_rgba(4,30,66,0.55)] transition-[colors,top]
      duration-300 hover:bg-gold sm:top-auto sm:bottom-6"
    :class="promoOpen ? 'top-20' : 'top-4'"
    :aria-label="`سبد سفارش، ${toFa(cart.itemCount)} کالا`"
    @click="$emit('open')"
  >
    <ShoppingBag :size="22" />
    <span
      v-if="cart.itemCount"
      class="tnum absolute -end-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center
        rounded-full bg-gold px-1 text-[11px] font-bold text-white"
      aria-live="polite"
    >
      {{ toFa(cart.itemCount) }}
    </span>
  </button>
</template>
