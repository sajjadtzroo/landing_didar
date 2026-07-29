/**
 * Base URL for the API. On the server (SSR) we call the internal container URL;
 * in the browser we use the public URL. `credentials: include` so the admin
 * session cookie rides along.
 */
export function useApiBase(): string {
  const config = useRuntimeConfig()
  return import.meta.server
    ? (config.apiBaseInternal as string)
    : config.public.apiBase
}

export function apiFetch<T>(path: string, opts: Parameters<typeof $fetch>[1] = {}) {
  return $fetch<T>(`${useApiBase()}${path}`, {
    credentials: 'include',
    ...opts,
  })
}
