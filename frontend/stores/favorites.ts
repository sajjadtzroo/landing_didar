import { defineStore } from 'pinia'
import type { Product } from '~/types'

// Client source of truth for the wishlist (guest + logged-in mirror). Persisted
// to localStorage like the cart, so a guest keeps favorites across refreshes and
// they survive until synced to the account on login (see useFavorites).
export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    items: [] as Product[],
  }),

  getters: {
    count: (state) => state.items.length,
    isFavorite: (state) => (productId: string) =>
      state.items.some((p) => p.id === productId),
  },

  actions: {
    // Returns true if the product is now favorited (added), false if removed.
    toggle(product: Product): boolean {
      const i = this.items.findIndex((p) => p.id === product.id)
      if (i >= 0) {
        this.items.splice(i, 1)
        return false
      }
      this.items.push(product)
      return true
    },
    remove(productId: string) {
      this.items = this.items.filter((p) => p.id !== productId)
    },
    // Replace with the union of current + server products (dedup by id). Used to
    // reconcile after login without dropping guest picks.
    mergeIn(products: Product[]) {
      const byId = new Map(this.items.map((p) => [p.id, p]))
      for (const p of products) byId.set(p.id, p)
      this.items = [...byId.values()]
    },
  },

  persist: true,
})
