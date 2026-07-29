<script setup lang="ts">
import { ShoppingBag } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { toFa } from '~/utils/format'

defineEmits<{ open: [] }>()

const cart = useCartStore()
const bubble = ref<HTMLElement | null>(null)

// Subtle scale pulse on count change (momentum feel, §2b). Reduced-motion safe:
// the Web Animations call is cheap and honored by the OS setting.
watch(
  () => cart.itemCount,
  (n, prev) => {
    if (import.meta.server || n <= prev || !bubble.value) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    bubble.value.animate(
      [{ transform: 'scale(0.9)' }, { transform: 'scale(1.08)' }, { transform: 'scale(1)' }],
      { duration: 320, easing: 'cubic-bezier(0.2,0,0,1)' },
    )
  },
)
</script>

<template>
  <Transition name="pop">
    <button
      v-show="cart.itemCount > 0"
      id="cart-bubble"
      ref="bubble"
      type="button"
      class="fixed bottom-5 end-5 z-30 flex h-16 w-16 items-center justify-center
        rounded-full bg-navy text-cream shadow-luxury transition hover:bg-gold"
      :aria-label="`سبد سفارش، ${toFa(cart.itemCount)} کالا`"
      @click="$emit('open')"
    >
      <ShoppingBag :size="24" />
      <span
        class="tnum absolute -end-1 -top-1 flex h-6 min-w-6 items-center justify-center
          rounded-full bg-gold px-1 text-xs font-bold text-white"
      >
        {{ toFa(cart.itemCount) }}
      </span>
    </button>
  </Transition>
</template>

<style scoped>
.pop-enter-active,
.pop-leave-active {
  transition: transform 0.2s cubic-bezier(0.2, 0, 0, 1), opacity 0.2s ease;
}
.pop-enter-from,
.pop-leave-to {
  transform: scale(0);
  opacity: 0;
}
</style>
