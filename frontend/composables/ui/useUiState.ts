/**
 * Global storefront UI state (cart drawer, order sheet, success overlay), shared
 * across the landing and product pages via useState so the navbar / cart bubble
 * work from any route. Handlers live here, not in a single page.
 */
export function useUiState() {
  const cartOpen = useState('ui-cart-open', () => false)
  const orderOpen = useState('ui-order-open', () => false)
  const successRef = useState<string | null>('ui-success-ref', () => null)

  const cart = useCartStore()
  const { trackEvent, clearEcommerceCart } = useAnalytics()

  function openCart() {
    cartOpen.value = true
    trackEvent('cart', 'open_drawer', undefined, cart.itemCount)
  }

  function openOrder() {
    cartOpen.value = false
    orderOpen.value = true
  }

  function onOrderSuccess(payload: { reference: string }) {
    orderOpen.value = false
    successRef.value = payload.reference
    cart.clear()
    clearEcommerceCart()
  }

  return { cartOpen, orderOpen, successRef, openCart, openOrder, onOrderSuccess }
}
