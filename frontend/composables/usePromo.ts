/**
 * Shared visibility state for the top promotion banner. The navs read it to
 * offset themselves below the banner, and PromoBanner dismisses it.
 */
export function usePromo() {
  const open = useState('promo-open', () => true)
  return { open }
}
