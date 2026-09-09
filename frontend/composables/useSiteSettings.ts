interface SiteSettings {
  price_requires_login: boolean
}

// Fetched once per SSR render / client session. Cached by Nuxt via key.
export function useSiteSettings() {
  const base = useApiBase()
  return useFetch<SiteSettings>('/settings', {
    baseURL: base,
    key: 'site-settings',
    default: (): SiteSettings => ({ price_requires_login: false }),
  })
}
