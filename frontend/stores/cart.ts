import { defineStore } from 'pinia'
import type { CartItem, Product } from '~/types'

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [] as CartItem[],
  }),

  getters: {
    itemCount: (state) => state.items.reduce((n, i) => n + i.quantity, 0),
    // Sum of priced items only; "on request" items don't contribute a number.
    total: (state) =>
      state.items.reduce(
        (sum, i) => sum + (i.price != null ? i.price * i.quantity : 0),
        0,
      ),
    isSelected: (state) => (productId: string) =>
      state.items.some((i) => i.productId === productId),
    quantityOf: (state) => (productId: string) =>
      state.items.find((i) => i.productId === productId)?.quantity ?? 0,
  },

  actions: {
    addItem(product: Product, quantity = 1) {
      const existing = this.items.find((i) => i.productId === product.id)
      if (existing) {
        existing.quantity += quantity
        return
      }
      this.items.push({
        productId: product.id,
        name: product.name,
        sku: product.sku,
        price: product.price != null ? Number(product.price) : null,
        imageUrl: product.image_url,
        quantity,
      })
    },
    updateQuantity(productId: string, quantity: number) {
      const item = this.items.find((i) => i.productId === productId)
      if (!item) return
      if (quantity <= 0) {
        this.removeItem(productId)
        return
      }
      item.quantity = quantity
    },
    removeItem(productId: string) {
      this.items = this.items.filter((i) => i.productId !== productId)
    },
    clear() {
      this.items = []
    },
  },

  // Survive a refresh (client-side localStorage). See pinia-plugin-persistedstate.
  persist: true,
})
