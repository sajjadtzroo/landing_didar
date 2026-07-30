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

  // SSR on for SEO; admin is client-only (session-gated, no SEO value).
  routeRules: {
    '/admin/**': { ssr: false },
    // `/` isn't a landing itself — the 3 live at /l/<slug>. Send it to the first.
    '/': { redirect: '/l/one' },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'fa', dir: 'rtl' },
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#041E42' },
      ],
    },
  },

  runtimeConfig: {
    // Server-only: used by useFetch during SSR (container→container in docker).
    apiBaseInternal: process.env.NUXT_API_BASE_INTERNAL || 'http://localhost:8000/api/v1',
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
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
