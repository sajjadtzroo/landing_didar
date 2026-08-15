# Frontend — Nuxt 3, domain-grouped

Persian/RTL storefront + admin/agent/account panels for Didar Gold. This app
mirrors the backend's modular-monolith layout (`backend/app/domains/CLAUDE.md`):
code is grouped **by domain**, not by technical kind alone. Deviations need a
written reason here.

## Structure

```
frontend/
├── components/          # auto-imported; names stay flat (pathPrefix: false)
│   ├── ui/              # generic widgets — NO domain knowledge
│   ├── layout/          # site chrome: navs, footer, promo banner/popup
│   ├── catalog/         # products & shop browsing (cards, grid, filters, …)
│   ├── content/         # landing/CMS sections: hero, FAQ, trust, portfolios
│   ├── orders/          # cart + checkout: drawer, fabs, order form, success
│   ├── account/         # customer panel shell
│   ├── admin/           # admin panel chrome (sidebar, headers, stat cards)
│   ├── chat/            # support-chat widget
│   └── pricing/         # live gold-rate strip
├── composables/
│   ├── useApi.ts        # cross-domain core (SSR-aware base URL + apiFetch) — stays at root
│   ├── core/            # useSiteUrl, useMediaUrl, useClientLog
│   ├── analytics/       # useAnalytics (Matomo), useMautic
│   ├── ui/              # useToast, useUiState, useDragDismiss, useFlyToCart, usePromo
│   ├── account/         # useCustomerAuth, useCustomerUpload, useFavorites
│   ├── admin/           # useAdminUpload
│   ├── catalog/         # useShopFilters
│   └── chat/            # useChatSocket, useSupportChat
├── stores/              # Pinia (Nuxt convention — flat): adminAuth, cart, favorites
├── pages/               # routed by URL (Nuxt convention): account/ admin/ agent/ l/ products/ shop/
├── layouts/  middleware/  plugins/  server/   # Nuxt conventions — flat
├── utils/               # pure helpers (format, orderSchema, chart, landingContent)
├── constants/  types/   # shared content strings / TS types
└── tests/               # Vitest: tests/utils, tests/stores (+ fixtures)
```

Backend domain map for orientation: catalog, orders, customers→`account/`,
content, agents, users→`admin/`, pricing, chat.

## Rules (the contract)

- **Pages stay thin.** A page composes components + composables; domain logic
  lives in the domain's folder, not inline in a page.
- **`ui/` has no domain knowledge.** Nothing in `components/ui/` or
  `composables/ui/` may import stores, API types, or domain composables that
  tie it to one feature. If it knows what a "product" is, it isn't `ui/`.
- **New code goes in its domain folder.** New cart piece → `orders/`;
  new landing section → `content/`; generic widget → `ui/`.
- **Component names stay flat and globally unique.** `nuxt.config.ts` scans
  `components/` with `pathPrefix: false`, so `<ProductCard>` resolves no matter
  which subfolder holds it — and two files may never share a basename.
- **Composables auto-import via `imports.dirs = ['composables/**']`.** Adding a
  new subfolder needs no config change (the glob covers it).
- **`useApi.ts` stays at composables root** — it is the cross-domain core every
  domain calls; nothing in it may become domain-specific.
- Cross-domain use is fine at the component level (a page mixes domains), but
  keep shared logic in `core/`/`ui/` rather than importing one domain's
  composable from another domain's.

## Lint / test / build

No Node on the host — run the gates in Docker (from repo root):

```bash
docker run --rm \
  -v "$PWD/frontend:/app" -w /app \
  -e npm_config_sharp_libvips_binary_host=https://registry.npmmirror.com/-/binary/sharp-libvips \
  node:22-alpine sh -c "npm ci --legacy-peer-deps && npm run lint && npm run test && npm run build"
```

Or via compose (production image build, uses `frontend/Dockerfile`):

```bash
docker compose build frontend
```

All three gates (`lint`, `test` — 25 specs, `build`) must be green before
commit.
