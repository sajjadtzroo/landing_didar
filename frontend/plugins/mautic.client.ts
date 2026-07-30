/**
 * Mautic marketing-automation tracker. Loads mtc.js, tracks the initial page
 * view and every SPA route change (the default snippet only fires once).
 * Lead capture (identifying a contact on order submit) goes through
 * composables/useMautic.ts, which pushes to the same global `mt` queue.
 */
declare global {
  interface Window {
    MauticTrackingObject?: string
    mt?: ((...args: unknown[]) => void) & { q?: unknown[][] }
  }
}

export default defineNuxtPlugin(() => {
  const { public: cfg } = useRuntimeConfig()
  const url = ((cfg.mauticUrl as string) || '').replace(/\/$/, '')
  if (!url) return // not configured => no-op (dev)

  window.MauticTrackingObject = 'mt'
  window.mt =
    window.mt ||
    function (...args: unknown[]) {
      ;(window.mt!.q = window.mt!.q || []).push(args)
    }

  const s = document.createElement('script')
  s.async = true
  s.src = `${url}/mtc.js`
  document.head.appendChild(s)

  window.mt('send', 'pageview')

  const router = useRouter()
  router.afterEach((to) => {
    window.mt?.('send', 'pageview', { url: location.origin + to.fullPath })
  })
})
