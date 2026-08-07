<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
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
const {
  trackEvent,
  addEcommerceItem,
  trackEcommerceCartUpdate,
} = useAnalytics()

const qty = ref(1)
const imageEl = ref<HTMLElement | null>(null)

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
    addEcommerceItem(i.sku, i.name, 'jewelry', i.price ?? 0, i.quantity)
  }
  trackEcommerceCartUpdate(cart.total)
}
</script>

<template>
  <main v-if="product" class="pt-16 sm:pt-20">
    <div class="mx-auto max-w-content px-5 py-10 sm:px-10">
      <!-- Breadcrumb -->
      <nav class="mb-8 flex items-center gap-2 text-sm text-ink-muted" aria-label="مسیر">
        <NuxtLink to="/" class="hover:text-gold-text">خانه</NuxtLink>
        <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
        <NuxtLink to="/products" class="hover:text-gold-text">{{ CONTENT.products.title }}</NuxtLink>
        <ChevronLeft :size="14" class="rotate-180" aria-hidden="true" />
        <span class="text-ink">{{ product.name }}</span>
      </nav>

      <div class="grid gap-10 lg:grid-cols-2">
        <!-- Image -->
        <div ref="imageEl" class="aspect-square overflow-hidden border border-line bg-media-surface">
          <NuxtImg
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.name"
            class="h-full w-full object-cover"
            width="800"
            height="800"
            format="webp"
            sizes="(max-width: 1024px) 100vw, 600px"
            fetchpriority="high"
          />
        </div>

        <!-- Details -->
        <div class="flex flex-col">
          <h1 class="text-3xl font-medium text-ink sm:text-4xl">{{ product.name }}</h1>

          <!-- اجرت (making fee) is the customer-facing figure — no Toman price -->
          <p class="tnum mt-4 text-2xl text-gold-text">
            <template v-if="product.ojrat_percent">
              {{ CONTENT.products.ojrat }} {{ toFa(Number(product.ojrat_percent)) }}٪
            </template>
            <template v-else>{{ CONTENT.products.priceOnRequest }}</template>
          </p>

          <dl class="mt-6 grid grid-cols-2 gap-y-3 border-y border-line py-6 text-sm">
            <dt class="text-ink-muted">{{ CONTENT.products.sku }}</dt>
            <dd class="text-end text-ink">{{ product.sku }}</dd>
            <template v-if="product.weight_grams">
              <dt class="text-ink-muted">{{ CONTENT.products.weight }}</dt>
              <dd class="tnum text-end text-ink">
                {{ toFa(Number(product.weight_grams)) }} {{ CONTENT.products.gram }}
              </dd>
            </template>
            <template v-if="product.karat">
              <dt class="text-ink-muted">{{ CONTENT.products.karat }}</dt>
              <dd class="tnum text-end text-ink">{{ toFa(product.karat) }}</dd>
            </template>
          </dl>

          <p v-if="product.description" class="mt-6 text-base leading-8 text-ink-muted">
            {{ product.description }}
          </p>

          <div class="mt-8 flex items-center gap-4">
            <QtyStepper v-model="qty" />
            <button
              type="button"
              class="flex h-[58px] flex-1 items-center justify-center bg-navy text-base
                font-medium text-white transition duration-300 hover:bg-gold"
              @click="addToCart"
            >
              {{ CONTENT.products.add }}
            </button>
          </div>
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
          />
        </div>
      </section>
    </div>
  </main>
</template>
