import { defineStore } from 'pinia'
import type { CartItem, Product } from '~/types'

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [] as CartItem[],
  }),

  getters: {
    itemCount: (state) => state.items.reduce((n, i) => n + i.quantity, 0),
    // Total weight in grams (wholesale gold is quantified by weight, not Toman).
    // Single number = midpoint sum; kept for order/analytics which need a scalar.
    total: (state) =>
      state.items.reduce(
        (sum, i) => sum + (i.weightGrams != null ? i.weightGrams * i.quantity : 0),
        0,
      ),
    // Weight as a min–max range scaled by quantity — sets vary in weight
    // (2× «۱۲-۱۵ گرم» = «۲۴-۳۰ گرم»). A single-weight piece adds that value to
    // both ends. Display only.
    totalWeightRange(state): { min: number; max: number } {
      let min = 0
      let max = 0
      for (const i of state.items) {
        const m = i.weightDisplay?.match(/([\d.]+)\s*[-–]\s*([\d.]+)/)
        const lo = m ? Number(m[1]) : (i.weightGrams ?? 0)
        const hi = m ? Number(m[2]) : (i.weightGrams ?? 0)
        min += lo * i.quantity
        max += hi * i.quantity
      }
      return { min, max }
    },
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
        weightGrams: product.weight_grams != null ? Number(product.weight_grams) : null,
        weightDisplay: product.weight_display ?? null,
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
