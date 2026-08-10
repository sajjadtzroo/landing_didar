<script setup lang="ts">
import { CONTENT } from '~/constants/content'
import type { Landing } from '~/types'
import { resolveContent } from '~/utils/landingContent'

// One landing, keyed by slug. Every section's content (hero text/media, trust
// cards, product groups, faq, footer, promo, section toggles) comes from the
// landing's `content` blob; `resolveContent` fills any gap from CONTENT defaults.
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

// Resolved, always-complete content for this landing. The layout resolves promo/
// footer chrome itself (SSR-safe), so this page only drives its own sections.
const c = computed(() => resolveContent(landing.value?.content))
const groups = computed(() => landing.value?.groups || [])

const canonical = `${useSiteUrl()}/l/${slug}`

useHead(() => ({
  title: `${landing.value?.title || CONTENT.brand} — ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: c.value.hero.supporting },
    { property: 'og:title', content: landing.value?.title || CONTENT.brand },
    { property: 'og:description', content: c.value.hero.supporting },
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
  script: c.value.faq.length
    ? [{
        type: 'application/ld+json',
        innerHTML: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'FAQPage',
          mainEntity: c.value.faq.map((f) => ({
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
      v-if="c.sections.hero"
      :video-url="landing?.hero_video_url || undefined"
      :poster-url="landing?.hero_poster_url || undefined"
      :eyebrow="c.hero.eyebrow"
      :headline="c.hero.headline"
      :supporting="c.hero.supporting"
      :cta="c.hero.cta"
      @order="scrollToProducts"
    />
    <TrustBar v-if="c.sections.trust" :items="c.trust" />
    <template v-if="c.sections.products">
      <ProductGrid
        v-for="(g, i) in groups"
        :key="i"
        carousel
        :flush="i > 0"
        :anchor-id="i === 0 ? 'products' : `products-${i}`"
        :products="g.products"
        :eyebrow="g.eyebrow ?? undefined"
        :title="g.title"
        :description="g.description ?? undefined"
        :view-all-to="i === groups.length - 1 ? '/shop' : undefined"
      />
    </template>
    <FaqAccordion v-if="c.sections.faq" id="faq" :faqs="c.faq" />
  </main>
</template>
