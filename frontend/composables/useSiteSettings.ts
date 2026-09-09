interface SiteSettings {
  price_requires_login: boolean
}

// Reads the site settings payload fetched once in the default layout.
// Components use this to get an already-resolved value (no SSR timing issues).
export function useSiteSettings() {
  return useNuxtData<SiteSettings>('site-settings')
}
