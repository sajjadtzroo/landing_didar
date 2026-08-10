/**
 * Base URL for the API. On the server (SSR) we call the internal container URL;
 * in the browser we use the public URL. `credentials: include` so the admin
 * session cookie rides along.
 */
export function useApiBase(): string {
  const config = useRuntimeConfig()
  if (import.meta.server) return config.apiBaseInternal as string
  // Any HTTPS deployment talks same-origin through the nitro proxy (see
  // nuxt.config routeRules) so the session cookie is FIRST-party — Safari/iOS
  // drop cross-site cookies (liara.run is a public suffix). Local dev over
  // plain http keeps the configured absolute base (no proxy in dev).
  if (location.protocol === 'https:') return '/api/v1'
  return config.public.apiBase
}

/** Correlation id sent as X-Request-ID; the backend echoes it and stamps every
 * server log line with it, so a browser failure can be joined to server logs. */
function requestId(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID().replace(/-/g, '')
    : Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export function apiFetch<T>(path: string, opts: Parameters<typeof $fetch>[1] = {}) {
  const rid = requestId()
  return $fetch<T>(`${useApiBase()}${path}`, {
    credentials: 'include',
    ...opts,
    headers: { 'X-Request-ID': rid, ...(opts.headers as Record<string, string>) },
    onResponseError({ response }) {
      // 5xx = server fault the user can't fix — report it (client errors are
      // expected flow: 401 guard, 409 business rules, 422 validation).
      if (response.status >= 500 && import.meta.client) {
        reportClientError({
          event: 'nuxt.api.server_error',
          module: 'nuxt.api',
          message: `${response.status} on ${path} (request_id=${rid})`,
          url: window.location.href,
        })
      }
    },
  })
}
