import { beforeEach, describe, expect, it } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useCartStore } from '~/stores/cart'
import { makeProduct } from '../fixtures/product'

describe('cart store', () => {
  beforeEach(() => {
    localStorage.clear()
    const pinia = createPinia()
    // Same plugin the Nuxt app registers — lets us assert the persisted shape.
    // Pinia only activates queued plugins once installed on a Vue app.
    pinia.use(piniaPluginPersistedstate)
    createApp({}).use(pinia)
    setActivePinia(pinia)
  })

  it('addItem maps a Product into a CartItem (weight string → number)', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct({ weight_grams: '12.5' }))
    expect(cart.items).toEqual([
      {
        productId: 'p1',
        name: 'انگشتر طلا',
        sku: 'SKU-001',
        weightGrams: 12.5,
        imageUrl: '/img/p1.jpg',
        quantity: 1,
      },
    ])
  })

  it('addItem for an existing product increments quantity instead of duplicating', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct(), 2)
    cart.addItem(makeProduct(), 3)
    expect(cart.items).toHaveLength(1)
    expect(cart.items[0].quantity).toBe(5)
  })

  it('itemCount sums quantities across lines', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct({ id: 'a' }), 2)
    cart.addItem(makeProduct({ id: 'b' }), 3)
    expect(cart.itemCount).toBe(5)
  })

  it('total is weight in grams × quantity, treating null weight as 0', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct({ id: 'a', weight_grams: '10' }), 2) // 20g
    cart.addItem(makeProduct({ id: 'b', weight_grams: null }), 4) // price-on-request, 0g
    expect(cart.total).toBe(20)
  })

  it('updateQuantity sets the quantity, and removes the line at qty <= 0', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct())
    cart.updateQuantity('p1', 7)
    expect(cart.quantityOf('p1')).toBe(7)
    cart.updateQuantity('p1', 0)
    expect(cart.isSelected('p1')).toBe(false)
    expect(cart.items).toHaveLength(0)
  })

  it('updateQuantity on an unknown product is a no-op', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct())
    cart.updateQuantity('nope', 3)
    expect(cart.items).toEqual([expect.objectContaining({ productId: 'p1', quantity: 1 })])
  })

  it('removeItem and clear empty the cart', () => {
    const cart = useCartStore()
    cart.addItem(makeProduct({ id: 'a' }))
    cart.addItem(makeProduct({ id: 'b' }))
    cart.removeItem('a')
    expect(cart.items.map((i) => i.productId)).toEqual(['b'])
    cart.clear()
    expect(cart.itemCount).toBe(0)
  })

  it('persists its items to localStorage under the store id ("cart")', async () => {
    const cart = useCartStore()
    cart.addItem(makeProduct(), 2)
    await nextTick() // persistedstate writes on the pre-flush subscription
    const raw = localStorage.getItem('cart')
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw!)).toEqual({
      items: [expect.objectContaining({ productId: 'p1', quantity: 2 })],
    })
  })
})
