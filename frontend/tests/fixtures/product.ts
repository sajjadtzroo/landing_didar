import type { Product } from '~/types'

/** Minimal valid Product for store tests; override per-case. */
export function makeProduct(over: Partial<Product> = {}): Product {
  return {
    id: 'p1',
    name: 'انگشتر طلا',
    slug: 'gold-ring',
    sku: 'SKU-001',
    description: null,
    weight_grams: '12.5',
    karat: 18,
    price: null,
    ojrat_percent: null,
    image_url: '/img/p1.jpg',
    images: [],
    category: 'daily',
    product_status: 'sellable',
    warrantable: true,
    is_active: true,
    sort_order: 0,
    ...over,
  }
}
