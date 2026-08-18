/**
 * Product image URLs served straight from /media — no IPX. The photos are
 * pre-optimized webp (a 640px card variant `<name>-sm.webp` + the full file),
 * so we skip on-the-fly optimization (which re-encoded per request with a 60s
 * cache) and let the browser + edge cache the immutable files instead.
 */
export function useProductImage() {
  const media = useMediaUrl()
  const sm = (path?: string | null) =>
    path && path.endsWith('.webp') ? path.replace(/\.webp$/, '-sm.webp') : path
  return {
    // Card / thumbnail size (~640px, ~20KB).
    card: (path?: string | null) => media(sm(path)),
    // Full resolution (detail hero).
    full: (path?: string | null) => media(path),
  }
}
