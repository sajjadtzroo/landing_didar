/**
 * Hand-rolled Matomo tracker (fewer deps than @nuxt/scripts, full control).
 * Loads matomo.js, tracks the initial page view, and — crucially — tracks every
 * SPA route change (the default snippet only fires once on load).
 */
export default defineNuxtPlugin(() => {
  const { public: cfg } = useRuntimeConfig()
  const url = cfg.matomoUrl as string
  const siteId = cfg.matomoSiteId as string
  if (!url || !siteId) return // not configured => no-op (dev)

  const _paq = (window._paq = window._paq || [])
  _paq.push(['enableLinkTracking'])
  _paq.push(['enableHeartBeatTimer', 15])
  if (location.protocol === 'https:') _paq.push(['setSecureCookie', true])
  _paq.push(['trackPageView'])

  const base = url.endsWith('/') ? url : `${url}/`
  _paq.push(['setTrackerUrl', `${base}matomo.php`])
  _paq.push(['setSiteId', siteId])

  const s = document.createElement('script')
  s.async = true
  s.src = `${base}matomo.js`
  document.head.appendChild(s)

  // SPA route tracking — without this, only the first page view is recorded.
  const router = useRouter()
  router.afterEach((to, from) => {
    _paq.push(['setReferrerUrl', from.fullPath])
    _paq.push(['setCustomUrl', to.fullPath])
    _paq.push(['setDocumentTitle', document.title])
    _paq.push(['trackPageView'])
  })
})
