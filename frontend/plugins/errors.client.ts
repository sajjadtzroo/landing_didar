/**
 * Global browser error capture → backend log ingest. Without this, client-side
 * crashes die in the user's console and the team never hears about them.
 * Events land in Loki under module=nuxt.client / nuxt.router.
 */
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('vue:error', (error, _instance, info) => {
    const err = error as Error
    reportClientError({
      event: 'nuxt.vue.error',
      message: `${err?.message ?? error} (${info})`,
      stack: err?.stack,
      url: window.location.href,
    })
  })

  nuxtApp.hook('app:error', (error) => {
    reportClientError({
      event: 'nuxt.app.error',
      message: String((error as Error)?.message ?? error),
      stack: (error as Error)?.stack,
      url: window.location.href,
    })
  })

  window.addEventListener('unhandledrejection', (e) => {
    reportClientError({
      event: 'nuxt.promise.unhandled',
      message: String(e.reason?.message ?? e.reason),
      stack: e.reason?.stack,
      url: window.location.href,
    })
  })

  window.addEventListener('error', (e) => {
    // Resource load failures have no error object; capture the message anyway.
    reportClientError({
      event: 'nuxt.window.error',
      message: e.message || `resource error: ${(e.target as HTMLElement)?.tagName}`,
      stack: e.error?.stack,
      url: window.location.href,
    })
  })

  const router = useRouter()
  router.onError((error) => {
    reportClientError({
      event: 'nuxt.router.error',
      module: 'nuxt.router',
      message: String(error?.message ?? error),
      stack: error?.stack,
      url: window.location.href,
    })
  })

  window.addEventListener('pagehide', flushClientLogs)
})
