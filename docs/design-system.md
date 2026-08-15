# Didar Gold — Design System

> Source of truth: `frontend/tailwind.config.ts` + `frontend/assets/css/main.css`
> (Nuxt 3, Tailwind). Documents what the code actually renders, not an
> aspirational spec. Luxury gold-and-navy jewelry brand, RTL-first (Persian),
> light + dark themes via `[data-theme]` on `:root` (admin/agent layouts pin
> `data-theme="light"`; the admin login screen pins `dark`).
>
> History: this file started life as an extraction from an older React
> prototype (`src/index.css`); it was renamed from `DESIGN_SYSTEM copy.md` and
> now tracks the live Nuxt frontend.

---

## 1. Color palette

### Brand constants (identical in both themes — static hex, support Tailwind `/opacity` modifiers)

| Token | Hex | Tailwind class | Use |
|---|---|---|---|
| Gold | `#B08A57` | `gold` | Decorative lines, fills, hover accents, `::selection` |
| Gold soft | `#D9B985` | `gold-soft` | Borders on raised cards / trust icons, logo fill on dark |
| Navy | `#041E42` | `navy` | Primary button bg, footer, `theme-color`, navy-tinted shadows |
| Navy deep | `#020B17` | `navy-deep` | Dark-mode footer / deepest contrast, admin-login card |
| Cream | `#F7F3EE` | `cream` | Light surface base, text on navy |
| Cream bright | `#FFFCF7` | `cream-bright` | Trust-icon chip bg, top of shop gradient bands |
| Cream deep | `#EFE6D6` | `cream-deep` | Deepest cream band — shop/product section closer (`ProductGrid`) |
| Danger bright | `#FFB4AB` | `danger-bright` | Error text on the always-navy admin login screen |

### Theme-aware semantic tokens (CSS variables, resolve per `[data-theme]` — **no** alpha modifiers)

| Token | Light | Dark | Meaning |
|---|---|---|---|
| `--surface` | `#F7F3EE` | `#07182F` | Page background |
| `--surface-soft` | `#F2F0EB` | `#0B2342` | Subtle fill, skeleton base, chat bubbles/table heads |
| `--surface-raised` | `#FFFAF3` | `#102B4D` | Cards, raised panels |
| `--ink` | `#041E42` | `#F7F3EE` | Primary text |
| `--ink-muted` | navy @65% | cream @66% | Secondary text |
| `--gold-text` | `#835F26` | `#C8A063` | **Accessible** gold for text (AA 4.5:1); focus ring |
| `--line` | gold @25% | gold-soft @26% | Borders, dividers |
| `--header` | cream @90% | navy @90% | Sticky header bg |
| `--media-surface` | `#F2F0EB` | `#173454` | Image placeholders |
| `--footer` | `#041E42` | `#020B17` | Footer |

Tailwind classes mirror the variable names: `bg-surface`, `bg-surface-soft`,
`bg-surface-raised`, `text-ink`, `text-ink-muted`, `text-gold-text`,
`border-line`, `bg-header`, `bg-media-surface`, `bg-footer`.
There is **no** `surface-2` token — use `surface-soft`.

### Status colors (separate from brand — AA-tuned per theme)

| Token | Light text / soft bg | Dark text / soft bg | Tailwind |
|---|---|---|---|
| Danger | `#B3261E` / `#FCEBEA` | `#FF8A80` / 10% | `danger` / `danger-soft` |
| Success | `#1E7A46` / `#E7F4EC` | `#5FD394` / 12% | `success` / `success-soft` |
| Warning | `#8A5B00` / `#FBF1DD` | `#FFC96B` / 12% | `warning` / `warning-soft` |

Status badge recipe: `bg-danger-soft text-danger` (soft bg + strong text of the
same family). Solid status buttons: `bg-danger text-white hover:brightness-90`.
Never reach for raw Tailwind palette classes (`bg-red-600`, `text-green-800`,
`bg-amber-100`, …) — they bypass theming and break dark mode.

> ⚠️ **Accessibility rule baked in:** raw brand gold `#B08A57` only reaches
> ~2.8:1 on cream. For **text**, always use `text-gold-text`. Reserve `gold`
> for decorative lines/fills only.

---

## 2. Typography

- **Font:** `Doran` (self-hosted woff2 in `frontend/public/fonts/`,
  `font-display: swap`), fallbacks `Vazirmatn`, `system-ui`, `sans-serif`.
  Applied globally on `html/body/#__nuxt` and as Tailwind `font-sans`.
- **Weights loaded:** 300 Light · 400 Regular · 500 Medium · 700 Bold.
- **Tabular figures:** add `.tnum` on prices/quantities/dates so numerals
  don't jitter.
- **Scale in use** (from components):

| Role | Classes |
|---|---|
| Hero H1 | `text-[42px] sm:text-[58px] lg:text-[68px]` · `leading-[1.42]` · `tracking-[-0.03em]` |
| Section H2 | `text-4xl sm:text-5xl font-normal` |
| Card title | `text-lg` / `text-2xl` · `font-medium` |
| Eyebrow | `text-[11px] sm:text-xs` · `tracking-[0.24em]` · uppercase Latin |
| Body | `text-lg sm:text-xl` · `leading-9`, muted `text-ink-muted` |
| Meta / links | `text-sm` · `text-gold-text` |

---

## 3. Shape & radius — **sharp by design**

The brand is square-cornered. Two mechanisms enforce it:

1. `tailwind.config.ts` overrides `borderRadius` so every size (`sm`…`3xl`) = `0px`; only `full` = `9999px`.
2. `main.css` adds `[class*="rounded-"]:not(.rounded-full){ border-radius:0 !important }`.

Opt-in exceptions (class names dodge the `rounded-` selector on purpose):

- `.corner-soft` — 10px radius for storefront product cards / grouped chips.
- `.admin-card` (16px) / `.admin-subcard` (12px) — admin frosted-glass panels.

Only `rounded-full` (icon chips, avatars, FABs, chat bubbles' container) stays
circular. Any other `rounded-*` class renders square at runtime — treat it as
a dead value.

---

## 4. Elevation & motion

- **Shadows:** cards use `hover:shadow-lg` / `hover:shadow-xl`; the luxury
  lift is tokenized as `shadow-luxury` (`0 24px 65px rgba(4,30,66,0.16)` —
  navy-tinted). One-off navy/gold-tinted arbitrary shadows are allowed for
  FABs/nav chrome (they derive from brand hex).
- **Hover lift:** cards `hover:-translate-y-1` / `-translate-y-2`; images `group-hover:scale-105`.
- **Transitions:** `transition duration-300` standard; images `duration-700`;
  easing token `ease-standard` = `cubic-bezier(0.2, 0, 0, 1)`.
- **Reduced motion:** global `@media (prefers-reduced-motion)` clamps all
  animation/transition to `0.01ms`; the hero swaps `<video>` for a static
  `<img>`; skeleton shimmer freezes. Honor this in new work.
- **Reduced transparency:** `.chrome-blur`, `.admin-card`, `.admin-aura` all
  fall back to solid surfaces under `prefers-reduced-transparency`.
- **Focus:** always-visible `:focus-visible { outline: 2px solid var(--gold-text); offset 2px }`.

---

## 5. Components (as built)

### Buttons
`flex h-[58px] w-full items-center justify-center text-base font-medium text-white transition duration-300 disabled:opacity-60`
- **Primary (navy):** `bg-navy hover:bg-gold`
- **Accent (gold, admin login):** `bg-gold hover:bg-cream hover:text-navy`
- **Outline:** `border border-line hover:border-gold` (admin secondary) or `border-navy hover:bg-navy hover:text-white` (storefront view-all)
- Compact admin actions use `h-11`; submit buttons always carry a busy state
  (`:disabled` + «در حال …» label).

### Form control — `.form-control` (in `@layer components`)
`h-14 w-full border border-line bg-surface px-4 text-sm text-ink placeholder:text-ink-muted focus:border-gold`
(compact variant: add `h-11`; textareas: `h-auto py-3`).

Form conventions (see `components/ui/FormField.vue`):
- Every input is wrapped in `<FormField label … :error … required>` — visible
  label, `*` required marker, `role="alert"` error bound via
  `aria-describedby`. Dense admin/inline inputs may use `aria-label` instead.
- Phones: `type="tel" inputmode="numeric" dir="ltr" autocomplete="tel" maxlength="11"`.
- OTP: `inputmode="numeric" autocomplete="one-time-code"`.
- Credentials: `autocomplete="username|current-password|new-password"`.
- Checkout identity: `autocomplete="name|organization|address-level1|address-level2"`.
- Mobile keyboards: `enterkeyhint="search|send|next|go|done"` where the action
  is clear; validation on blur (vee-validate + zod on OrderForm), errors in Persian.

### Cards
| Card | Structure |
|---|---|
| **Product** (`catalog/ProductCard.vue`) | `.corner-soft border border-line bg-surface-raised` · square image on `bg-media-surface` · `hover:-translate-y-*` + shadow |
| **Skeleton** (`catalog/ProductCardSkeleton.vue`) | `.sk` blocks: `var(--surface-soft)` base + white shimmer, reduced-motion-aware |
| **Collection** (`content/CollectionCarousel.vue`) | full-bleed image + `bg-gradient-to-t from-black/75` overlay · white text bottom-start · ghost-gold CTA |
| **Trust item** (`content/TrustBar.vue`) | circular icon chip `rounded-full border-gold-soft bg-cream-bright` → hover navy invert |
| **Admin panel** (`.admin-card` / `.admin-subcard`) | frosted glass over `.admin-aura` glows; `--hover` modifier lifts 2px |

### Section shell (repeated pattern)
```html
<section class="bg-surface py-16">
  <div class="mx-auto max-w-content px-6 sm:px-10">
    <SectionDivider eyebrow="…" title="…" description="…" />
    …grid…
  </div>
</section>
```
The **gold hairline + ✦ divider** is the signature motif — use the
`.divider-star` component class (or `<SectionDivider>`); shop bands close with
a `cream-bright → cream → cream-deep` gradient.

---

## 6. Layout & RTL

- **Direction:** `<html lang="fa" dir="rtl">`. Use **logical properties** —
  `start/end`, `ms-/me-`, `ps-/pe-`, `border-e` — never `left/right`.
- **Container widths (tokens):** `max-w-content` (1280px), `max-w-hero`
  (1450px), `max-w-wide` (1800px).
- **Section padding:** `py-16` vertical; `px-5 sm:px-8` / `px-6 sm:px-10` horizontal.
- **Grid rhythm:** products `grid-cols-2 … lg:grid-cols-4/5`; collections/trust `md:grid-cols-3|5`.
- **Breakpoints:** default Tailwind (`sm` 640 · `md` 768 · `lg` 1024); prefer `min-h-dvh` over `100vh`.
- **LTR islands:** phone numbers, serial codes, slugs, URLs and credentials get
  `dir="ltr"` (+ `.tnum` for digits).

---

## Quick reference (drop-in Tailwind snippets)

```html
<!-- Primary button -->
<button class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white transition duration-300 hover:bg-gold disabled:opacity-60">…</button>

<!-- Card -->
<article class="corner-soft overflow-hidden border border-line bg-surface-raised transition duration-300 hover:-translate-y-2 hover:shadow-xl">…</article>

<!-- Section divider motif -->
<div class="divider-star">✦</div>

<!-- Status badge -->
<span class="bg-success-soft px-2 py-1 text-xs text-success">تأیید شده</span>

<!-- Accessible gold text --> <p class="text-gold-text">…</p>
<!-- Decorative gold only -->  <span class="h-px w-12 bg-gold"></span>

<!-- Labeled field -->
<FormField label="شماره موبایل" :error="errors.phone" required v-slot="{ id, describedBy }">
  <input :id="id" type="tel" inputmode="numeric" dir="ltr" autocomplete="tel"
         class="form-control" :aria-describedby="describedBy" />
</FormField>
```
