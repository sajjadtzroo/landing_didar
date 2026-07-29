<script setup lang="ts">
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { FAQ, Product } from '~/types'

// SSR fetch — products & FAQs land in the initial payload (SEO + no client refetch).
// Explicit `key` is REQUIRED: the base URL differs server (backend:8000) vs client
// (localhost:8001), so without a stable key the client computes a different auto-key,
// misses the payload, and refetches — briefly/permanently emptying the grid.
const base = useApiBase()
const { data: products } = await useFetch<Product[]>('/products', {
  baseURL: base,
  key: 'products',
  default: () => [],
})
const { data: faqs } = await useFetch<FAQ[]>('/faqs', {
  baseURL: base,
  key: 'faqs',
  default: () => [],
})

useHead({
  title: `${CONTENT.brand} — ${CONTENT.hero.headline}`,
  meta: [{ name: 'description', content: CONTENT.hero.supporting }],
})

const cart = useCartStore()
const { trackEvent } = useAnalytics()

const cartOpen = ref(false)
const orderOpen = ref(false)
const successRef = ref<string | null>(null)

function scrollToProducts() {
  document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })
}

function openCart() {
  cartOpen.value = true
  trackEvent('cart', 'open_drawer', undefined, cart.itemCount)
}

function openOrder() {
  cartOpen.value = false
  orderOpen.value = true
}

function onSuccess(payload: { reference: string }) {
  orderOpen.value = false
  successRef.value = payload.reference
  cart.clear()
  useAnalytics().clearEcommerceCart()
}

// Scroll-depth milestones (25/50/75/100).
if (import.meta.client) {
  const fired = new Set<number>()
  const onScroll = useThrottleFn(() => {
    const h = document.documentElement
    const pct = ((h.scrollTop + window.innerHeight) / h.scrollHeight) * 100
    for (const m of [25, 50, 75, 100]) {
      if (pct >= m && !fired.has(m)) {
        fired.add(m)
        trackEvent('engagement', 'scroll_depth', undefined, m)
      }
    }
  }, 500)
  useEventListener(window, 'scroll', onScroll, { passive: true })
}
</script>

<template>
  <div>
    <StickyHeader @order="openOrder" />

    <main>
      <HeroSection @order="scrollToProducts" />
      <TrustBar />
      <ProductGrid :products="products || []" />
      <FaqAccordion :faqs="faqs || []" />
    </main>

    <ContactFooter />

    <!-- Floating cart + drawer -->
    <CartBubble @open="openCart" />
    <CartDrawer v-model="cartOpen" @continue="openOrder" />

    <!-- Order form sheet -->
    <BaseSheet v-model="orderOpen" :title="CONTENT.form.title">
      <OrderForm @success="onSuccess" />
    </BaseSheet>

    <!-- Success overlay -->
    <SuccessScreen v-if="successRef" :reference="successRef" />
  </div>
</template>
