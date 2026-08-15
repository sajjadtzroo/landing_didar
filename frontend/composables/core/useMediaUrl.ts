/**
 * Resolve a stored media path to a loadable URL.
 *
 * Local uploads come back as backend-relative "/media/<name>", served by the API
 * host (not the frontend), so a bare "/media/..." src 404s against the frontend
 * origin. Prepend the API origin. Absolute URLs (CDN / MinIO / presigned) pass
 * through unchanged.
 */
export function useMediaUrl() {
  const origin = useApiBase().replace(/\/api\/v1\/?$/, '')
  return (path: string | null | undefined): string => {
    if (!path) return ''
    if (/^https?:\/\//i.test(path)) return path
    return origin + (path.startsWith('/') ? path : '/' + path)
  }
}
