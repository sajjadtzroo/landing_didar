<script setup lang="ts">
import { ChevronLeft, Heart } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'
import { toFa } from '~/utils/format'

const route = useRoute()
const slug = route.params.slug as string

// Single product (SSR). Stable per-slug key so the client reuses the payload.
const { data: product } = await useFetch<Product>(`/products/${slug}`, {
  baseURL: useApiBase(),
  key: `product-${slug}`,
})
if (!product.value) {
  throw createError({ statusCode: 404, statusMessage: 'Product not found', fatal: true })
}

// Related: other active products (reuse the cached list payload).
const { data: all } = await useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})
const related = computed(() =>
  (all.value || []).filter((p) => p.slug !== slug).slice(0, 4),
)

const cart = useCartStore()
const { toast } = useToast()
const { isFav, toggle } = useFavorites()
const { full, card } = useProductImage()
const {
  trackEvent,
  addEcommerceItem,
  trackEcommerceCartUpdate,
} = useAnalytics()

const qty = ref(1)
const imageEl = ref<HTMLElement | null>(null)

// Gallery: MinIO-imported photos, falling back to the single image_url.
const active = ref(0)
const gallery = computed(() => {
  const imgs = product.value?.images ?? []
  if (imgs.length) return imgs
  return product.value?.image_url ? [product.value.image_url] : []
})
const mainSrc = computed(() => gallery.value[active.value] ?? null)

// Category eyebrow (mirrors the shop collection labels).
const categoryLabel = computed(() =>
  product.value ? CONTENT.products[product.value.category]?.title : '',
)

// Sample pieces (نمونه) are shown for reference but can't be ordered.
const isSample = computed(() => product.value?.product_status === 'sample')

// Spec tiles: weight leads (the wholesale value signal), then عیار + اجرت —
// same value hierarchy as the shop cards.
const specs = computed(() => {
  const p = product.value
  if (!p) return []
  const rows: { label: string; value: string }[] = []
  if (p.weight_display || p.weight_grams) {
    rows.push({
      label: CONTENT.products.weight,
      value: p.weight_display
        ? toFa(p.weight_display)
        : `${toFa(Number(p.weight_grams))} ${CONTENT.products.gram}`,
    })
  }
  rows.push({ label: CONTENT.products.karat, value: p.karat ? toFa(p.karat) : '—' })
  rows.push({
    label: CONTENT.products.ojrat,
    value: p.ojrat_percent
      ? `${toFa(Number(p.ojrat_percent))}٪`
      : CONTENT.products.priceOnRequest,
  })
  return rows
})

const canonical = `${useSiteUrl()}/products/${slug}`

useHead(() => ({
  title: `${product.value?.name} | ${CONTENT.brand}`,
  meta: [
    { name: 'description', content: product.value?.description || '' },
    { property: 'og:image', content: product.value?.image_url || '' },
    { property: 'og:title', content: product.value?.name || '' },
    { property: 'og:description', content: product.value?.description || '' },
    { property: 'og:type', content: 'product' },
    { property: 'og:url', content: canonical },
  ],
  link: [{ rel: 'canonical', href: canonical }],
  script: product.value
    ? [{
        type: 'application/ld+json',
        innerHTML: JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'Product',
          name: product.value.name,
          sku: product.value.sku,
          description: product.value.description || undefined,
          image: product.value.image_url || undefined,
          brand: { '@type': 'Brand', name: CONTENT.brand },
        }),
      }]
    : [],
}))

onMounted(() => {
  if (product.value) trackEvent('products', 'view_item', product.value.name)
})

function addToCart() {
  if (!product.value) return
  cart.addItem(product.value, qty.value)
  flyToCart(imageEl.value, product.value.image_url)
  trackEvent('cart', 'add', product.value.name, qty.value)
  for (const i of cart.items) {
    addEcommerceItem(i.sku, i.name, 'jewelry', i.weightGrams ?? 0, i.quantity)
  }
  trackEcommerceCartUpdate(cart.total)
}

async function onHeart() {
  if (!product.value) return
  const added = await toggle(product.value)
  toast(added ? CONTENT.account.favAddedToast : CONTENT.account.favRemovedToast)
}
</script>

<template>
  <main v-if="product" class="pt-16 sm:pt-20">
    <div class="mx-auto max-w-content px-5 py-10 sm:px-10">
      <!-- Breadcrumb -->
      <nav class="mb-8 flex items-center gap-2 text-sm text-ink-muted" aria-label="مسیر">
        <NuxtLink to="/" class="hover:text-gold-text">{{ CONTENT.nav.home }}</NuxtLink>
        <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
        <NuxtLink to="/shop" class="hover:text-gold-text">{{ CONTENT.nav.shop }}</NuxtLink>
        <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
        <span class="text-ink">{{ product.name }}</span>
      </nav>

      <div class="grid gap-10 lg:grid-cols-2">
        <!-- Gallery: main image + thumbnail strip (photos imported from MinIO) -->
        <div class="flex flex-col gap-3">
          <div
            ref="imageEl"
            class="corner-soft relative aspect-square overflow-hidden border border-line bg-white"
          >
            <!-- Full-res webp straight from /media (no IPX). -->
            <img
              v-if="mainSrc"
              :src="full(mainSrc)"
              :alt="product.name"
              class="h-full w-full object-contain"
              width="800"
              height="800"
              fetchpriority="high"
            />
            <!-- Fallback when a product has no imagery yet (parity with cards) -->
            <div v-else class="flex h-full w-full items-center justify-center" aria-hidden="true">
              <BrandLogo :height="48" color="#D9B985" />
            </div>
            <!-- Favorite heart -->
            <button
              type="button"
              class="absolute start-3 top-3 z-10 flex h-11 w-11 items-center justify-center
                rounded-full bg-surface/80 backdrop-blur transition hover:bg-surface"
              :aria-label="CONTENT.account.favoritesTitle"
              :aria-pressed="isFav(product.id)"
              @click="onHeart"
            >
              <Heart
                :size="20"
                :class="isFav(product.id) ? 'fill-danger text-danger' : 'text-ink-muted'"
                aria-hidden="true"
              />
            </button>
          </div>
          <div v-if="gallery.length > 1" class="grid grid-cols-5 gap-2">
            <button
              v-for="(src, i) in gallery"
              :key="src"
              type="button"
              class="corner-soft aspect-square overflow-hidden border bg-white transition"
              :class="i === active ? 'border-gold' : 'border-line hover:border-navy'"
              :aria-label="`نمایش تصویر ${toFa(i + 1)}`"
              :aria-current="i === active"
              @click="active = i"
            >
              <img
                :src="card(src)"
                :alt="`${product.name} — ${toFa(i + 1)}`"
                class="h-full w-full object-contain"
                width="120"
                height="120"
                loading="lazy"
              />
            </button>
          </div>
        </div>

        <!-- Details -->
        <div class="flex flex-col">
          <p v-if="categoryLabel" class="mb-2 text-xs tracking-[0.25em] text-gold-text sm:text-sm">
            {{ categoryLabel }}
          </p>
          <h1 class="text-3xl font-medium text-ink sm:text-4xl">{{ product.name }}</h1>
          <p class="tnum mt-2 text-sm text-ink-muted">{{ CONTENT.products.sku }} {{ product.sku }}</p>

          <!-- Spec tiles: weight-first value hierarchy (matches the shop cards) -->
          <div class="mt-6 grid grid-cols-3 gap-3">
            <div
              v-for="s in specs"
              :key="s.label"
              class="corner-soft border border-line bg-surface-raised p-4 text-center"
            >
              <p class="text-xs text-ink-muted">{{ s.label }}</p>
              <p class="tnum mt-1 text-base font-medium text-gold-text sm:text-lg">{{ s.value }}</p>
            </div>
          </div>

          <!-- whitespace-pre-line: descriptions are multi-paragraph (line breaks
               are meaningful headings/sections), so preserve them. -->
          <p
            v-if="product.description"
            class="mt-6 whitespace-pre-line text-base leading-8 text-ink-muted"
          >
            {{ product.description }}
          </p>

          <p
            v-if="isSample"
            class="corner-soft mt-8 border border-line bg-surface-soft px-4 py-3 text-center text-sm text-ink-muted"
          >
            {{ CONTENT.products.sampleNote }}
          </p>
          <div v-else class="mt-8 flex items-center gap-3">
            <QtyStepper v-model="qty" />
            <button
              type="button"
              class="flex h-[58px] flex-1 items-center justify-center bg-navy text-base
                font-medium text-white transition duration-300 hover:bg-gold"
              @click="addToCart"
            >
              {{ CONTENT.shop.addToCart }}
            </button>
            <button
              type="button"
              class="flex h-[58px] w-[58px] shrink-0 items-center justify-center border border-line
                transition hover:border-gold"
              :aria-label="CONTENT.account.favoritesTitle"
              :aria-pressed="isFav(product.id)"
              @click="onHeart"
            >
              <Heart
                :size="22"
                :class="isFav(product.id) ? 'fill-danger text-danger' : 'text-ink-muted'"
                aria-hidden="true"
              />
            </button>
          </div>

          <!-- Signature gold hairline -->
          <span class="mt-8 h-px w-full bg-gradient-to-l from-transparent via-gold to-transparent" aria-hidden="true" />
        </div>
      </div>

      <!-- Related -->
      <section v-if="related.length" class="mt-20">
        <SectionDivider :title="CONTENT.products.related" />
        <div class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
          <ProductCard
            v-for="(p, i) in related"
            :key="p.id"
            :product="p"
            :index="i"
            shop
          />
        </div>
      </section>
    </div>
  </main>
</template>
