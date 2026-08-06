import type { LandingContent } from '~/utils/landingContent'

// Bridges per-landing content from the landing page ([slug].vue) up to the shared
// chrome in the layout (PromoBanner / PromoPopup / ContactFooter). Null on
// non-landing pages → chrome falls back to CONTENT defaults.
export interface LandingChrome {
  sections: LandingContent['sections']
  promoText: string
  footer: LandingContent['footer']
}

export function useLandingChrome() {
  return useState<LandingChrome | null>('landing-chrome', () => null)
}
