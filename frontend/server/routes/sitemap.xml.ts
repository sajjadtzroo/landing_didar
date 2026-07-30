import type { Product } from '~/types'

// Dynamic sitemap: 3 landings + /products + one URL per active product.
// Small fixed URL set, so a Nitro route beats pulling in a sitemap module.
export default defineEventHandler(async (event) => {
  const cfg = useRuntimeConfig(event)
  const site = (cfg.public.siteUrl as string).replace(/\/$/, '')

  const urls = ['/l/one', '/l/two', '/l/three', '/products']

  try {
    const products = await $fetch<Product[]>('/products', { baseURL: cfg.apiBaseInternal })
    for (const p of products) urls.push(`/products/${p.slug}`)
  } catch {
    // API down at build/request time — still emit the static routes.
  }

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${site}${u}</loc></url>`).join('\n')}
</urlset>`

  setResponseHeader(event, 'content-type', 'application/xml; charset=utf-8')
  return body
})
