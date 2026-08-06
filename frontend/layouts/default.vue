<script setup lang="ts">
import { computed, watch } from 'vue'
import { CONTENT } from '~/constants/content'

// Global storefront chrome. One nav per context: the landing (/l/*) uses the
// bottom tubelight pill; storefront pages (/products, …) use the top glass navbar.
const { cartOpen, orderOpen, successRef, openCart, openOrder, onOrderSuccess } =
  useUiState()
const route = useRoute()
const isLanding = computed(() => route.path.startsWith('/l'))

// Per-landing content for the shared chrome (promo/footer), set by [slug].vue.
// Reset when leaving landings so storefront pages fall back to CONTENT defaults.
const chrome = useLandingChrome()
watch(isLanding, (v) => { if (!v) chrome.value = null }, { immediate: true })

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
    <NavBar v-if="!isLanding" @order="openOrder" />
    <template v-if="isLanding">
      <TubelightNav />
      <CartFab @open="openCart" />
    </template>

    <slot />

    <!-- Promo/footer read per-landing `chrome` set by [slug].vue during its setup.
         They MUST render after <slot/> so the page has published chrome first
         (they're fixed/teleported, so DOM order here is visually irrelevant). -->
    <PromoBanner
      v-if="!isLanding || chrome?.sections.promo !== false"
      :text="chrome?.promoText"
    />
    <PromoPopup
      v-if="isLanding && chrome?.sections.promo !== false"
      :text="chrome?.promoText"
    />

    <ContactFooter
      v-if="!isLanding || chrome?.sections.footer !== false"
      id="footer"
      :footer="chrome?.footer"
    />

    <!-- Cart lives inside the TubelightNav pill now (no separate floating bubble). -->
    <CartDrawer v-model="cartOpen" @continue="openOrder" />

    <!-- Order form sheet -->
    <BaseSheet v-model="orderOpen" :title="CONTENT.form.title">
      <OrderForm @success="onOrderSuccess" />
    </BaseSheet>

    <!-- Success overlay -->
    <SuccessScreen v-if="successRef" :reference="successRef" />

    <!-- Global toast host (aria-live), for add-to-cart / favorite confirmations -->
    <AppToast />
  </div>
</template>
