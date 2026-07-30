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

const canonical = `${useSiteUrl()}/l/${slug}`

useHead(() => ({
  title: `${landing.value?.title || CONTENT.brand} — ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: CONTENT.hero.supporting },
    { property: 'og:title', content: landing.value?.title || CONTENT.brand },
    { property: 'og:description', content: CONTENT.hero.supporting },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: canonical },
    ...(landing.value?.hero_poster_url
      ? [{ property: 'og:image', content: landing.value.hero_poster_url }]
      : []),
  ],
  link: [
    { rel: 'canonical', href: canonical },
    // The hero poster is the LCP candidate — preload it (URL is per-landing).
    ...(landing.value?.hero_poster_url
      ? [{ rel: 'preload', as: 'image', href: landing.value.hero_poster_url, fetchpriority: 'high' }]
      : []),
  ],
  script: (faqs.value || []).length
    ? [{
        type: 'application/ld+json',
        innerHTML: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'FAQPage',
          mainEntity: (faqs.value || []).map((f) => ({
            '@type': 'Question',
            name: f.question,
            acceptedAnswer: { '@type': 'Answer', text: f.answer },
          })),
        }),
      }]
    : [],
}))

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
    <ProductGrid id="products" :products="landing?.products || []" carousel />
    <FaqAccordion id="faq" :faqs="faqs || []" />
  </main>
</template>
