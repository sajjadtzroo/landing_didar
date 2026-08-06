// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },

  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
    'pinia-plugin-persistedstate/nuxt',
    '@nuxt/image',
    '@vueuse/nuxt',
  ],

  css: ['~/assets/css/main.css'],

  // Pre-compress built JS/CSS (gzip + brotli) so the server serves compressed
  // bundles even without a proxy. Liara's ingress gzips dynamic HTML in prod.
  nitro: {
    compressPublicAssets: { gzip: true, brotli: true },
  },

  // SSR on for SEO; admin is client-only (session-gated, no SEO value).
  routeRules: {
    '/admin/**': { ssr: false },
    // Customer panel is session-gated (no SEO value) — render client-side.
    '/account/**': { ssr: false },
    // Landings are identical per visitor (cart is client-side), so cache the
    // rendered HTML with stale-while-revalidate — serves instantly, revalidates
    // in the background. Biggest SSR throughput win. Staleness ceiling: 60s.
    '/l/**': { swr: 60 },
    // `/` isn't a landing itself — the 3 live at /l/<slug>. Send it to the first.
    '/': { redirect: '/l/one' },
    // Baseline security headers. No strict CSP: Nuxt's inline hydration script
    // would need a nonce and the Lighthouse CSP audit is informative (0 weight).
    '/**': {
      headers: {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
      },
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'fa', dir: 'rtl' },
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' },
        // Preload only the above-the-fold Doran weights (h1=500, body=400).
        // font-display: swap already covers the rest.
        { rel: 'preload', as: 'font', type: 'font/woff2', href: '/fonts/Doran-Regular.woff2', crossorigin: '' },
        { rel: 'preload', as: 'font', type: 'font/woff2', href: '/fonts/Doran-Medium.woff2', crossorigin: '' },
        // Product imagery is served off this host — resolve DNS/TLS early.
        { rel: 'preconnect', href: 'https://didargold.com', crossorigin: '' },
      ],
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#041E42' },
      ],
    },
  },

  runtimeConfig: {
    // Server-only: used by useFetch during SSR (container→container in docker).
    apiBaseInternal: process.env.NUXT_API_BASE_INTERNAL || 'http://localhost:8000/api/v1',
    // Upstream for the first-party Mautic proxy (server/routes/mtc/[...].ts).
    mauticOrigin: process.env.NUXT_MAUTIC_ORIGIN || 'https://marketing-auto.liara.run',
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
      // Canonical origin — canonical/og:url/sitemap all build off this. Set the
      // real domain via NUXT_PUBLIC_SITE_URL in prod.
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'https://didargold.com',
      // Mautic marketing-automation base URL (visitor tracking + lead capture).
      mauticUrl: process.env.NUXT_PUBLIC_MAUTIC_URL || '',
      matomoUrl: process.env.NUXT_PUBLIC_MATOMO_URL || '',
      matomoSiteId: process.env.NUXT_PUBLIC_MATOMO_SITE_ID || '',
      // Matomo Goal / custom-dimension IDs (created in the Matomo UI).
      matomoGoalOrder: process.env.NUXT_PUBLIC_MATOMO_GOAL_ORDER || '1',
      matomoGoalPhone: process.env.NUXT_PUBLIC_MATOMO_GOAL_PHONE || '2',
      matomoDimProvince: process.env.NUXT_PUBLIC_MATOMO_DIM_PROVINCE || '1',
      matomoDimSource: process.env.NUXT_PUBLIC_MATOMO_DIM_SOURCE || '2',
    },
  },

  image: {
    format: ['avif', 'webp'],
    // Product imagery is served from the live Didar site + placeholder host.
    domains: ['didargold.com', 'placehold.co'],
  },
})
