<script setup lang="ts">
import { CONTENT } from '~/constants/content'
import type { FAQ, Landing } from '~/types'

// One of three landings, keyed by slug. Same layout as the old `/` page; only
// the hero video and the product set differ (both come from the API).
const route = useRoute()
const slug = route.params.slug as string
const base = useApiBase()

// Per-slug key: base URL differs server vs client, so a stable explicit key is
// required or the client refetches and flashes empty (see the old index.vue note).
const { data: landing, error } = await useFetch<Landing>(`/landings/${slug}`, {
  baseURL: base,
  key: `landing-${slug}`,
})
if (error.value || !landing.value) {
  throw createError({ statusCode: 404, statusMessage: 'Landing not found', fatal: true })
}

const { data: faqs } = await useFetch<FAQ[]>('/faqs', {
  baseURL: base,
  key: 'faqs',
  default: () => [],
})

useHead({
  title: `${CONTENT.brand} — ${CONTENT.hero.headline}`,
  meta: [{ name: 'description', content: CONTENT.hero.supporting }],
})

const { trackEvent } = useAnalytics()

function scrollToProducts() {
  document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })
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
  <main>
    <HeroSection
      :video-url="landing?.hero_video_url || undefined"
      :poster-url="landing?.hero_poster_url || undefined"
      @order="scrollToProducts"
    />
    <TrustBar />
    <ProductGrid id="products" :products="landing?.products || []" />
    <FaqAccordion id="faq" :faqs="faqs || []" />
  </main>
</template>
