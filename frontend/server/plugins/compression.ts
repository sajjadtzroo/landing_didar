import { gzipSync } from 'node:zlib'

// Gzip SSR HTML responses. compressPublicAssets covers static /_nuxt bundles but
// not the dynamic HTML document, which is on the FCP/LCP critical path. A managed
// proxy (Liara) would do this, but this guarantees it regardless of deploy target.
export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('render:response', (response, { event }) => {
    const enc = getRequestHeader(event, 'accept-encoding') || ''
    const ct = String(response.headers?.['content-type'] || '')
    if (!ct.includes('text/html') || typeof response.body !== 'string' || !enc.includes('gzip')) return
    const buf = gzipSync(response.body)
    response.body = buf as unknown as string
    response.headers = {
      ...response.headers,
      'content-encoding': 'gzip',
      'content-length': String(buf.length),
    }
  })
})
