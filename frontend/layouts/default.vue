<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

// Global storefront chrome. One nav per context: the landing (/l/*) uses the
// bottom tubelight pill; storefront pages (/products, …) use the top glass navbar.
const { cartOpen, orderOpen, successRef, openCart, openOrder, onOrderSuccess } =
  useUiState()
const route = useRoute()
const isLanding = computed(() => route.path.startsWith('/l'))

const siteUrl = useSiteUrl()
useHead({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: CONTENT.brand,
      url: siteUrl,
      logo: `${siteUrl}/logo.svg`,
      telephone: CONTENT.phone,
      sameAs: [CONTENT.instagram, CONTENT.telegram],
    }),
  }],
})
</script>

<template>
  <div>
    <PromoBanner />
    <NavBar v-if="!isLanding" @order="openOrder" />
    <template v-if="isLanding">
      <TubelightNav />
      <CartFab @open="openCart" />
    </template>

    <slot />

    <ContactFooter id="footer" />

    <!-- Cart lives inside the TubelightNav pill now (no separate floating bubble). -->
    <CartDrawer v-model="cartOpen" @continue="openOrder" />

    <!-- Order form sheet -->
    <BaseSheet v-model="orderOpen" :title="CONTENT.form.title">
      <OrderForm @success="onOrderSuccess" />
    </BaseSheet>

    <!-- Success overlay -->
    <SuccessScreen v-if="successRef" :reference="successRef" />
  </div>
</template>
