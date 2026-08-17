<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Landing } from '~/types'
import { resolveContent } from '~/utils/landingContent'

// Global storefront chrome. One nav per context: the landing (/l/*) uses the
// bottom tubelight pill; storefront pages (/products, …) use the top glass navbar.
const { cartOpen, orderOpen, successRef, openCart, openOrder, onOrderSuccess } =
  useUiState()
const route = useRoute()
const isLanding = computed(() => route.path.startsWith('/l'))
// The promo strip + nav are both fixed; when the promo is open the nav drops by
// its height (top-20 sm:top-14). Page content pads for the nav only, so without
// matching that shift the fixed nav clips the first heading (کاتالوگ محصولات).
const { open: promoOpen } = usePromo()

// The Promo strip + Footer are shared chrome but their content/visibility are
// per-landing. The layout resolves them itself (rather than reading state the
// page sets) — on SSR the page is async and its setup runs AFTER the layout's
// render, so page-set state is never ready in time. This useFetch dedupes against
// the page's own `landing-<slug>` fetch (same key), so it's not a second request.
const slug = computed(() => (isLanding.value ? String(route.params.slug || '') : ''))
const { data: landingChrome } = await useFetch<Landing>(
  () => `/landings/${slug.value}`,
  {
    baseURL: useApiBase(),
    key: () => `landing-${slug.value}`,
    immediate: isLanding.value,
    watch: [slug],
    default: () => null,
  },
)
const chrome = computed(() => {
  if (!isLanding.value || !landingChrome.value) return null
  const c = resolveContent(landingChrome.value.content)
  return { sections: c.sections, promoText: c.promo.text, footer: c.footer }
})

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
    <PromoBanner
      v-if="!isLanding || chrome?.sections.promo !== false"
      :text="chrome?.promoText"
    />
    <NavBar v-if="!isLanding" @order="openOrder" />
    <template v-if="isLanding">
      <TubelightNav />
      <CartFab @open="openCart" />
      <PromoPopup v-if="chrome?.sections.promo !== false" :text="chrome?.promoText" />
    </template>

    <!-- Shift content down by the promo height when open, matching the nav's
         top-20 sm:top-14 shift, so headings clear the fixed nav. -->
    <div :class="!isLanding && promoOpen ? 'pt-20 sm:pt-14' : ''">
      <slot />
    </div>

    <ContactFooter
      v-if="!isLanding || chrome?.sections.footer !== false"
      id="footer"
      :footer="chrome?.footer"
    />

    <!-- Mobile bottom tab bar (storefront only); spacer keeps footer above it -->
    <template v-if="!isLanding">
      <div class="h-16 sm:hidden" aria-hidden="true" />
      <BottomNav />
    </template>

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

    <!-- Live support chat (client-only: WebSocket + auth state) -->
    <ClientOnly>
      <ChatWidget />
    </ClientOnly>
  </div>
</template>
