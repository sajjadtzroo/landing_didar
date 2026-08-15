// Canonical origin (no trailing slash), used by canonical/og:url tags.
export const useSiteUrl = () => useRuntimeConfig().public.siteUrl as string
