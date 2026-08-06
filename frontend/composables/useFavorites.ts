/**
 * Wishlist orchestrator. The persisted store (useFavoritesStore) is the client
 * source of truth so guests can favorite without an account. When logged in,
 * every change also hits the server, and on login the two are merged (guest
 * picks uploaded, server picks pulled) so nothing is lost across devices.
 */
import type { Product } from '~/types'

export function useFavorites() {
  const store = useFavoritesStore()
  const { customer } = useCustomerAuth()

  const isFav = (productId: string) => store.isFavorite(productId)

  // Toggle locally (instant), then mirror to the server if signed in.
  async function toggle(product: Product): Promise<boolean> {
    const nowFav = store.toggle(product)
    if (customer.value) {
      const method = nowFav ? 'PUT' : 'DELETE'
      await apiFetch(`/account/me/favorites/${product.id}`, { method }).catch(() => {})
    }
    return nowFav
  }

  // On login: upload guest picks, then pull the server list into the store so
  // both sides converge on the union.
  async function syncOnLogin() {
    if (import.meta.server) return
    try {
      await Promise.all(
        store.items.map((p) =>
          apiFetch(`/account/me/favorites/${p.id}`, { method: 'PUT' }).catch(() => {}),
        ),
      )
      const server = await apiFetch<Product[]>('/account/me/favorites')
      store.mergeIn(server)
    } catch {
      // offline / 401 — keep the local wishlist as-is
    }
  }

  return { store, isFav, toggle, syncOnLogin }
}
