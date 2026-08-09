import { useCompression } from 'h3-compression'

// Compress dynamic HTML at the beforeResponse layer — AFTER the route cache.
// Two reasons this is NOT a render:response hook:
//  1. render:response never fires on SWR cache HITS (routeRules swr), so cached
//     landings shipped uncompressed (~150KB raw HTML, ~600ms of mobile LCP).
//  2. mutating the body inside render:response gets the gzipped buffer STORED in
//     the cache as a string, corrupting it (the Aug-1 "incorrect header check").
// beforeResponse runs per-request for fresh AND cached responses; the cache only
// ever holds plain HTML. compressPublicAssets still covers static /_nuxt files.
export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('beforeResponse', async (event, response) => {
    const ct = String(getResponseHeader(event, 'content-type') || '')
    if (!ct.includes('text/html')) return
    if (getResponseHeader(event, 'content-encoding')) return // already encoded
    await useCompression(event, response)
  })
})
