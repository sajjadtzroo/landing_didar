import { nextTick, ref, watch } from 'vue'

// Shop filter state mirrored to the URL query, so a filtered/searched view is
// shareable, bookmarkable, and survives reload + back/forward. Short param keys
// keep the URL tidy: q, cat, sort, wmin, wmax, omin, omax, k.
export type ShopSort = 'newest' | 'weight_asc' | 'weight_desc'
const SORTS: ShopSort[] = ['newest', 'weight_asc', 'weight_desc']

function str(v: unknown): string {
  if (typeof v === 'string') return v
  if (Array.isArray(v) && typeof v[0] === 'string') return v[0]
  return ''
}
function asSort(v: unknown): ShopSort {
  const s = str(v)
  return (SORTS as string[]).includes(s) ? (s as ShopSort) : 'newest'
}
function asKarat(v: unknown): number | '' {
  const s = str(v)
  const n = Number(s)
  return s && !Number.isNaN(n) ? n : ''
}

export function useShopFilters() {
  const route = useRoute()
  const router = useRouter()
  const q0 = route.query

  const search = ref(str(q0.q))
  const category = ref(str(q0.cat)) // '' = all
  const sort = ref<ShopSort>(asSort(q0.sort))
  const weightMin = ref(str(q0.wmin))
  const weightMax = ref(str(q0.wmax))
  const ojratMin = ref(str(q0.omin))
  const ojratMax = ref(str(q0.omax))
  const karat = ref<number | ''>(asKarat(q0.k))

  // Guard so URL→state syncing doesn't immediately re-trigger state→URL.
  let syncing = false

  // state → URL (replace: no history spam, filters aren't navigation steps)
  watch(
    [search, category, sort, weightMin, weightMax, ojratMin, ojratMax, karat],
    () => {
      if (syncing) return
      const query: Record<string, string> = {}
      if (search.value.trim()) query.q = search.value.trim()
      if (category.value) query.cat = category.value
      if (sort.value !== 'newest') query.sort = sort.value
      if (weightMin.value) query.wmin = weightMin.value
      if (weightMax.value) query.wmax = weightMax.value
      if (ojratMin.value) query.omin = ojratMin.value
      if (ojratMax.value) query.omax = ojratMax.value
      if (karat.value !== '') query.k = String(karat.value)
      router.replace({ query })
    },
  )

  // URL → state (back/forward, or an external link into a filtered view)
  watch(
    () => route.query,
    (nq) => {
      syncing = true
      search.value = str(nq.q)
      category.value = str(nq.cat)
      sort.value = asSort(nq.sort)
      weightMin.value = str(nq.wmin)
      weightMax.value = str(nq.wmax)
      ojratMin.value = str(nq.omin)
      ojratMax.value = str(nq.omax)
      karat.value = asKarat(nq.k)
      nextTick(() => {
        syncing = false
      })
    },
  )

  function clear() {
    search.value = ''
    category.value = ''
    weightMin.value = ''
    weightMax.value = ''
    ojratMin.value = ''
    ojratMax.value = ''
    karat.value = ''
  }

  return {
    search,
    category,
    sort,
    weightMin,
    weightMax,
    ojratMin,
    ojratMax,
    karat,
    clear,
  }
}
