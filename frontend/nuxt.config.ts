// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },

  // Server sourcemaps make SSR stack traces readable in production logs.
  // Client maps stay off: they'd expose readable source to every visitor.
  sourcemap: { server: true, client: false },

  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
    'pinia-plugin-persistedstate/nuxt',
    '@nuxt/image',
    '@vueuse/nuxt',
    '@vite-pwa/nuxt',
  ],

  // components/ is grouped by domain (ui/, layout/, catalog/, …) purely for
  // code organisation. pathPrefix:false keeps registered names identical to
  // the flat layout (<ProductCard>, not <CatalogProductCard>) — zero template
  // churn. Filenames must therefore stay globally unique across subfolders.
  components: [{ path: '~/components', pathPrefix: false }],

  // Nuxt only auto-imports top-level composables/ by default; the glob makes
  // the domain subfolders (composables/ui, composables/account, …) scanned too.
  imports: { dirs: ['composables/**'] },

  css: ['~/assets/css/main.css'],

  // Pre-compress built JS/CSS (gzip + brotli) so the server serves compressed
  // bundles even without a proxy. Liara's ingress gzips dynamic HTML in prod.
  nitro: {
    compressPublicAssets: { gzip: true, brotli: true },
  },

  // Installable PWA (offline-capable shell + home-screen icon). SSR stays on for
  // SEO; the service worker precaches build assets and lets the app be installed.
  pwa: {
    registerType: 'autoUpdate',
    manifest: {
      name: 'دیدار گلد',
      short_name: 'دیدار گلد',
      description: 'فروشگاه آنلاین طلای ۱۸ عیار دیدار — بدون پرداخت آنلاین',
      lang: 'fa',
      dir: 'rtl',
      theme_color: '#041E42',
      background_color: '#041E42',
      display: 'standalone',
      start_url: '/',
      icons: [
        { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        { src: '/maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      // SSR app — don't SPA-fallback navigations; let each route render on the
      // server. The SW just precaches static build assets + icons/fonts.
      navigateFallback: undefined,
      globPatterns: ['**/*.{js,css,svg,png,woff2,ico}'],
    },
    // SW off during `nuxt dev` (avoids stale-cache surprises while iterating).
    devOptions: { enabled: false },
  },

  // SSR on for SEO; admin is client-only (session-gated, no SEO value).
  routeRules: {
    // First-party API proxy: didar-gold.liara.run and didar-gold-api.liara.run
    // are different SITES (liara.run is on the Public Suffix List), so a session
    // cookie set by the API is a third-party cookie — iOS Safari drops it and
    // mobile login breaks. Proxying makes every browser see one origin.
    // Override the target at build time with NUXT_PROXY_API_ORIGIN if needed.
    '/api/v1/**': {
      proxy: `${process.env.NUXT_PROXY_API_ORIGIN || 'https://didar-gold-api.liara.run'}/api/v1/**`,
    },
    '/media/**': {
      proxy: `${process.env.NUXT_PROXY_API_ORIGIN || 'https://didar-gold-api.liara.run'}/media/**`,
    },
    '/admin/**': { ssr: false },
    '/agent/**': { ssr: false },
    // Customer panel is session-gated (no SEO value) — render client-side.
    '/account/**': { ssr: false },
    // Landings are identical per visitor (cart is client-side), so cache the
    // rendered HTML with stale-while-revalidate — serves instantly, revalidates
    // in the background. Biggest SSR throughput win. Staleness ceiling: 60s.
    '/l/**': { swr: 60 },
    // Storefront pages are identical per visitor too (cart/favorites live
    // client-side) — same SWR win. Cached responses are compressed per-request
    // by server/plugins/compression.ts (beforeResponse), never in the cache.
    '/shop': { swr: 60 },
    '/shop/**': { swr: 60 },
    '/products/**': { swr: 60 },
    // Home is the storefront. Campaign landings still live at /l/<slug>.
    '/': { redirect: '/shop' },
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
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
        // PWA manifest — the module registers the SW but doesn't link the
        // manifest, so link it here to make the app installable.
        { rel: 'manifest', href: '/manifest.webmanifest' },
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
      // Chat WebSocket origin. The nitro proxy can't upgrade WS, so the browser
      // connects straight to the API host (auth = signed ticket, not cookie).
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || '',
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
      matomoGoalChat: process.env.NUXT_PUBLIC_MATOMO_GOAL_CHAT || '3',
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
