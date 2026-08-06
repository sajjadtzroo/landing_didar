import { CONTENT } from '~/constants/content'

// The per-landing content blob (mirrors backend core/content_defaults). Every
// field is optional in storage; `resolveContent` fills gaps from CONTENT so a
// landing (or a storefront page) always has complete, renderable content.
export interface TrustItem { icon: string; title: string; sub: string }
export interface FaqItem { question: string; answer: string }
export interface LandingFooter {
  tagline: string
  address: string
  hours: string
  phone: string
  phoneDisplay: string
  email: string
  whatsapp: string
  telegram: string
  instagram: string
  rights: string
}
export interface LandingHero {
  eyebrow: string
  headline: string
  supporting: string
  cta: string
}
export type SectionKey = 'promo' | 'hero' | 'trust' | 'products' | 'faq' | 'footer'
export interface LandingContent {
  sections: Record<SectionKey, boolean>
  promo: { text: string }
  hero: LandingHero
  trust: TrustItem[]
  faq: FaqItem[]
  footer: LandingFooter
  // groups live on the landing payload (resolved to products by the backend),
  // not here — the editor writes {title,eyebrow,description,product_ids} groups.
  groups?: unknown[]
}

// Frontend defaults derived from CONTENT — the fallback when a landing omits a
// field (or on non-landing pages that still render Promo/Footer chrome).
export function defaultContent(): LandingContent {
  return {
    sections: { promo: true, hero: true, trust: true, products: true, faq: true, footer: true },
    promo: { text: CONTENT.promo },
    hero: { ...CONTENT.hero },
    trust: [
      { icon: 'BadgeCheck', ...CONTENT.trust[0] },
      { icon: 'FileCheck', ...CONTENT.trust[1] },
      { icon: 'RefreshCw', ...CONTENT.trust[2] },
    ],
    faq: [], // FAQ items come from the landing's content (backend seeds them)
    footer: {
      tagline: CONTENT.footer.tagline,
      address: CONTENT.footer.address,
      hours: CONTENT.footer.hours,
      phone: CONTENT.phone,
      phoneDisplay: CONTENT.phoneDisplay,
      email: CONTENT.email,
      whatsapp: CONTENT.whatsapp,
      telegram: CONTENT.telegram,
      instagram: CONTENT.instagram,
      rights: CONTENT.footer.rights,
    },
  }
}

// Deep-merge a stored content blob over the defaults (missing/empty → default).
export function resolveContent(stored?: Partial<LandingContent> | null): LandingContent {
  const d = defaultContent()
  if (!stored) return d
  return {
    sections: { ...d.sections, ...(stored.sections || {}) },
    promo: { ...d.promo, ...(stored.promo || {}) },
    hero: { ...d.hero, ...(stored.hero || {}) },
    trust: stored.trust?.length ? stored.trust : d.trust,
    faq: stored.faq?.length ? stored.faq : d.faq,
    footer: { ...d.footer, ...(stored.footer || {}) },
    groups: stored.groups,
  }
}
