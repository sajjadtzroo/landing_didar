/**
 * The ONLY place that touches window._paq. Every call is SSR-guarded so the
 * server never sees it. Components import this, never _paq directly.
 */
declare global {
  interface Window {
    _paq?: unknown[][]
  }
}

function paq(): unknown[][] {
  if (import.meta.server) return []
  return (window._paq ||= [])
}

export function useAnalytics() {
  const trackEvent = (
    category: string,
    action: string,
    name?: string,
    value?: number,
  ) => paq().push(['trackEvent', category, action, name, value])

  const trackGoal = (goalId: number, revenue?: number) =>
    paq().push(['trackGoal', goalId, revenue])

  const setCustomDimension = (id: number, value: string) =>
    paq().push(['setCustomDimension', id, value])

  // --- Identity (visitor profile across devices/sessions) ---
  const setUserId = (id: string) => paq().push(['setUserId', id])

  const resetUserId = () => paq().push(['resetUserId'])

  // --- Ecommerce ---
  const addEcommerceItem = (
    sku: string,
    name: string,
    category: string,
    price: number,
    quantity: number,
  ) => paq().push(['addEcommerceItem', sku, name, category, price, quantity])

  const clearEcommerceCart = () => paq().push(['clearEcommerceCart'])

  const trackEcommerceCartUpdate = (grandTotal: number) =>
    paq().push(['trackEcommerceCartUpdate', grandTotal])

  const trackEcommerceOrder = (orderId: string, grandTotal: number) =>
    paq().push(['trackEcommerceOrder', orderId, grandTotal])

  return {
    trackEvent,
    trackGoal,
    setCustomDimension,
    setUserId,
    resetUserId,
    addEcommerceItem,
    clearEcommerceCart,
    trackEcommerceCartUpdate,
    trackEcommerceOrder,
  }
}
