# Didar Gold — Design System

> Extracted from the codebase (`tailwind.config.js`, `src/index.css`, `src/components/*`).
> Documents what the code actually renders, not an aspirational spec.
> Luxury gold-and-navy jewelry brand, RTL-first (Persian), light + dark themes.

---

## 1. Color palette

### Brand constants (identical in both themes — static hex, support Tailwind `/opacity` modifiers)

| Token | Hex | Tailwind class | Use |
|---|---|---|---|
| Gold | `#B08A57` | `gold` | Decorative lines, fills, hover accents, `::selection` |
| Gold soft | `#D9B985` | `gold-soft` | Borders on raised cards / trust icons |
| Navy | `#041E42` | `navy` | Primary button bg, footer, `theme-color` |
| Navy deep | `#020B17` | `navy-deep` | Dark-mode footer / deepest contrast |
| Cream | `#F7F3EE` | `cream` | Light surface base |
| Cream bright | `#FFFCF7` | `cream-bright` | Trust-icon chip bg |
| Danger bright | `#FFB4AB` | `danger-bright` | Error text on the always-navy Login screen |

### Theme-aware semantic tokens (CSS variables, resolve per `[data-theme]` — **no** alpha modifiers)

| Token | Light | Dark | Meaning |
|---|---|---|---|
| `--surface` | `#F7F3EE` | `#07182F` | Page background |
| `--surface-soft` | `#F2F0EB` | `#0B2342` | Subtle fill, skeleton base |
| `--surface-raised` | `#FFFAF3` | `#102B4D` | Cards, raised panels |
| `--ink` | `#041E42` | `#F7F3EE` | Primary text |
| `--ink-muted` | navy @65% | cream @66% | Secondary text |
| `--gold-text` | `#835F26` | `#C8A063` | **Accessible** gold for text (AA 4.5:1); focus ring |
| `--line` | gold @25% | gold-soft @26% | Borders, dividers |
| `--header` | cream @90% | navy @90% | Sticky header bg |
| `--contrast` / `-soft` / `-ink` / `-muted` | navy / white | navy-deep / cream | Inverted sections |
| `--media-surface` | `#F2F0EB` | `#173454` | Image placeholders |
| `--footer` | `#041E42` | `#020B17` | Footer |

### Status colors (separate from brand — AA-tuned per theme)

| Token | Light text / soft bg | Dark text / soft bg |
|---|---|---|
| Danger | `#B3261E` / `#FCEBEA` | `#FF8A80` / 10% |
| Success | `#1E7A46` / `#E7F4EC` | `#5FD394` / 12% |
| Warning | `#8A5B00` / `#FBF1DD` | `#FFC96B` / 12% |

> ⚠️ **Accessibility rule baked in:** raw brand gold `#B08A57` only reaches ~2.8:1 on
> cream. For **text**, always use `gold-text` (`text-gold-text`). Reserve `#B08A57`
> (`gold`) for decorative lines/fills only.

---

## 2. Typography

- **Font:** `Doran` (self-hosted woff2, `font-display: swap`), fallback `sans-serif`. Applied globally on `html/body/#root`.
- **Weights loaded:** 300 Light · 400 Regular · 500 Medium · 700 Bold.
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

1. `tailwind.config.js` overrides `borderRadius` so every size (`sm`…`3xl`) = `0px`; only `full` = `9999px`.
2. `src/index.css` adds `[class*="rounded-"]:not(.rounded-full){ border-radius:0 !important }`.

> Consequence: component classes like `rounded-[24px]`, `rounded-2xl`, `rounded-[28px]`
> are **overridden to 0 at runtime** — they render as sharp rectangles. Only `rounded-full`
> (trust-icon chips, avatars) stays circular. Treat those arbitrary radii as dead values;
> new components can omit `rounded-*` unless they want a circle.

---

## 4. Elevation & motion

- **Shadows:** cards use `hover:shadow-lg` / `hover:shadow-xl`; TrustBar uses a custom
  `shadow-[0_24px_65px_rgba(4,30,66,0.16)]` (navy-tinted luxury lift).
- **Hover lift:** cards `hover:-translate-y-1` / `-translate-y-2`; images `group-hover:scale-105`.
- **Transitions:** `transition duration-300` standard; images `duration-700`; theme swap
  `background-color/color 0.5s ease` on `body`.
- **Reduced motion:** global `@media (prefers-reduced-motion)` clamps all animation/transition
  to `0.01ms`. Hero also swaps its `<video>` for a static `<img>`. Honor this in new work.
- **Focus:** always-visible `:focus-visible { outline: 2px solid var(--gold-text); offset 2px }`.

---

## 5. Components (as built)

### Buttons — `h-[58px] w-[220px] flex items-center justify-center text-base font-medium text-white transition duration-300 hover:-translate-y-1`
- **Primary (navy):** `bg-navy hover:bg-gold`
- **Accent (gold):** `bg-gold hover:bg-navy`
- **Ghost-on-image:** `border border-gold px-5 py-2 text-sm hover:bg-gold` (over dark image overlays)

### Form control — `.form-control` (in `@layer components`)
`h-14 w-full border border-line bg-surface px-4 text-sm text-ink placeholder:text-ink-muted focus:border-gold`

### Cards
| Card | Structure |
|---|---|
| **Product** (`FeaturedProducts`) | `article` · `border border-line bg-surface-raised` · image `h-[220px] sm:h-[240px] object-cover` · centered body `px-5 py-5` · title `text-lg text-ink` · meta `text-sm text-ink-muted` · CTA `text-sm text-gold-text` · `hover:-translate-y-2 hover:shadow-xl` |
| **Collection** (`Collections`) | `group relative h-[290px]` · full-bleed image + `bg-gradient-to-t from-black/75 via-black/20` overlay · white text bottom-start · ghost-gold CTA · `group-hover:scale-105` (700ms) |
| **Article** (`ArticleCard.jsx`) | `border border-line bg-surface-raised` · image `h-[180px]` · body `px-5 py-5 text-start` · title `text-2xl font-medium` · meta `text-gold-text` · `hover:-translate-y-1 hover:shadow-lg` |
| **Trust item** (`TrustBar`) | grid cell `min-h-[168px]` · circular icon chip `h-[60px] w-[60px] rounded-full border-gold-soft bg-cream-bright` → `group-hover:bg-navy` + icon `group-hover:invert` · `border-e border-line` between cells |

> `ProductCard.jsx` and `CollectionCard.jsx` are **stubs** (`<div>Product Card</div>`).
> The live cards are inlined in the section components above.

### Section shell (repeated pattern)
```
<section className="bg-surface py-16">
  <div className="mx-auto max-w-[1280px|1800px] px-6 sm:px-10">
    <div className="mb-14 text-center">
      <h2 className="text-4xl sm:text-5xl font-normal text-ink">…</h2>
      <div className="mt-4 flex items-center justify-center gap-3 text-gold-text">
        <span className="h-px w-12 bg-gold" />✦<span className="h-px w-12 bg-gold" />
      </div>
    </div>
    …grid…
  </div>
</section>
```
The **gold hairline + ✦ divider** (`h-px w-12 bg-gold`) is the signature section motif.

### Loading — `.skeleton`
Shimmer gradient `surface-soft → line → surface-soft`, `animation: skeleton-shimmer 1.4s`,
frozen under reduced-motion.

---

## 6. Layout & RTL

- **Direction:** `<html lang="fa" dir="rtl">`. Use **logical properties** — `start/end`,
  `ms-/me-`, `ps-/pe-`, `border-e` — never `left/right`. Hero gradient flips on `language`.
- **Container widths:** `max-w-[1280px]` (content), `max-w-[1450px]` (hero), `max-w-[1800px]` (wide grids).
- **Section padding:** `py-16` vertical; `px-5 sm:px-8` / `px-6 sm:px-10` horizontal.
- **Grid rhythm:** products `grid-cols-2 md:grid-cols-3 lg:grid-cols-5`; collections/trust `md:grid-cols-3|5`.
- **Breakpoints:** default Tailwind (`sm` 640 · `md` 768 · `lg` 1024).

---

## Quick reference (drop-in Tailwind snippets)

```html
<!-- Primary button -->
<a class="flex h-[58px] w-[220px] items-center justify-center bg-navy text-base font-medium text-white transition duration-300 hover:-translate-y-1 hover:bg-gold">…</a>

<!-- Card -->
<article class="overflow-hidden border border-line bg-surface-raised transition duration-300 hover:-translate-y-2 hover:shadow-xl">…</article>

<!-- Section divider motif -->
<div class="flex items-center justify-center gap-3 text-gold-text"><span class="h-px w-12 bg-gold"></span>✦<span class="h-px w-12 bg-gold"></span></div>

<!-- Accessible gold text --> <p class="text-gold-text">…</p>
<!-- Decorative gold only -->  <span class="bg-gold h-px w-12"></span>
```
