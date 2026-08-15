<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Landing } from '~/types'
import { resolveContent } from '~/utils/landingContent'

// Global storefront chrome — ONE nav system everywhere. Landings used to swap
// to a bottom "tubelight" pill + cart fab, which read as a different site the
// moment you crossed /shop ↔ /l/*; they now share NavBar (desktop) +
// BottomNav (mobile). Landing-specific bits that remain are content, not
// chrome: promo strip/popup text and the per-landing footer visibility.
const { cartOpen, orderOpen, successRef, openOrder, onOrderSuccess } =
  useUiState()
const route = useRoute()
const isLanding = computed(() => route.path.startsWith('/l'))

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
    <NavBar @order="openOrder" />
    <PromoPopup
      v-if="isLanding && chrome?.sections.promo !== false"
      :text="chrome?.promoText"
    />

    <slot />

    <ContactFooter
      v-if="!isLanding || chrome?.sections.footer !== false"
      id="footer"
      :footer="chrome?.footer"
    />

    <!-- Mobile bottom tab bar; spacer keeps the footer above it -->
    <div class="h-16 sm:hidden" aria-hidden="true" />
    <BottomNav />

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
