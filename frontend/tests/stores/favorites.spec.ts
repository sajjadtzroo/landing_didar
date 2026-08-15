import { beforeEach, describe, expect, it } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useFavoritesStore } from '~/stores/favorites'
import { makeProduct } from '../fixtures/product'

describe('favorites store', () => {
  beforeEach(() => {
    localStorage.clear()
    const pinia = createPinia()
    // Pinia only activates queued plugins once installed on a Vue app.
    pinia.use(piniaPluginPersistedstate)
    createApp({}).use(pinia)
    setActivePinia(pinia)
  })

  it('toggle adds an unfavorited product and reports true', () => {
    const fav = useFavoritesStore()
    expect(fav.toggle(makeProduct())).toBe(true)
    expect(fav.count).toBe(1)
    expect(fav.isFavorite('p1')).toBe(true)
  })

  it('toggle removes an already-favorited product and reports false', () => {
    const fav = useFavoritesStore()
    fav.toggle(makeProduct())
    expect(fav.toggle(makeProduct())).toBe(false)
    expect(fav.count).toBe(0)
    expect(fav.isFavorite('p1')).toBe(false)
  })

  it('remove drops only the matching product', () => {
    const fav = useFavoritesStore()
    fav.toggle(makeProduct({ id: 'a' }))
    fav.toggle(makeProduct({ id: 'b' }))
    fav.remove('a')
    expect(fav.items.map((p) => p.id)).toEqual(['b'])
  })

  it('mergeIn unions guest + server favorites, deduped with server winning', () => {
    const fav = useFavoritesStore()
    fav.toggle(makeProduct({ id: 'a', name: 'guest copy' }))
    fav.toggle(makeProduct({ id: 'b' }))
    fav.mergeIn([makeProduct({ id: 'a', name: 'server copy' }), makeProduct({ id: 'c' })])
    expect(fav.items.map((p) => p.id).sort()).toEqual(['a', 'b', 'c'])
    expect(fav.items.find((p) => p.id === 'a')?.name).toBe('server copy')
  })

  it('persists to localStorage under the store id ("favorites")', async () => {
    const fav = useFavoritesStore()
    fav.toggle(makeProduct())
    await nextTick() // persistedstate writes on the pre-flush subscription
    const raw = localStorage.getItem('favorites')
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw!).items).toHaveLength(1)
  })
})
