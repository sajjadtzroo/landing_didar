<script setup lang="ts">
import { Check, Plus } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

// `shop` mode (storefront /shop) shows price + an add-to-cart button; the default
// (landing carousels) stays price-free, weight/اجرت only. Same card, one prop.
const props = defineProps<{ product: Product; index: number; shop?: boolean }>()

const cart = useCartStore()
const { openCart } = useUiState()
const selected = computed(() => cart.isSelected(props.product.id))
const qty = computed(() => cart.quantityOf(props.product.id))

function addToCart() {
  cart.addItem(props.product)
  openCart()
}
</script>

<template>
  <article
    class="corner-soft group relative cursor-pointer overflow-hidden border border-line
      bg-surface-raised transition duration-300 hover:-translate-y-2 hover:shadow-xl"
  >
    <NuxtLink
      :to="`/products/${product.slug}`"
      class="block w-full text-start"
      :aria-label="`${CONTENT.products.viewDetails}: ${product.name}`"
    >
      <div class="relative aspect-square overflow-hidden bg-media-surface">
        <NuxtImg
          v-if="product.image_url"
          :src="product.image_url"
          :alt="product.name"
          class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
          width="400"
          height="400"
          format="webp"
          sizes="(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 280px"
          :loading="index < 4 ? 'eager' : 'lazy'"
          :fetchpriority="index === 0 ? 'high' : undefined"
        />
        <!-- Selected · qty state (icon+text, never colour-only) -->
        <span
          v-if="selected"
          class="absolute end-2 top-2 flex items-center gap-1 bg-navy px-2 py-1 text-xs
            font-medium text-white"
        >
          ✓ {{ CONTENT.products.added }} · {{ toFa(qty) }}
        </span>
      </div>

      <div class="px-4 py-4">
        <h3 class="text-lg text-ink">{{ product.name }}</h3>
        <p class="mt-1 text-sm text-ink-muted">
          {{ CONTENT.products.sku }} {{ product.sku }}
        </p>
        <!-- Weight + اجرت (making fee) instead of price on cards -->
        <p
          v-if="product.weight_grams || product.ojrat_percent"
          class="tnum mt-3 text-sm text-gold-text"
        >
          <span v-if="product.weight_grams">
            {{ toFa(Number(product.weight_grams)) }} {{ CONTENT.products.gram }}
          </span>
          <span v-if="product.weight_grams && product.ojrat_percent" class="text-ink-muted"> · </span>
          <span v-if="product.ojrat_percent">
            {{ CONTENT.products.ojrat }} {{ toFa(Number(product.ojrat_percent)) }}٪
          </span>
        </p>
      </div>
    </NuxtLink>

    <!-- Shop mode: price + add-to-cart, OUTSIDE the link so it doesn't navigate -->
    <div v-if="shop" class="flex items-center justify-between gap-2 px-4 pb-4">
      <span class="tnum text-sm font-medium text-ink">
        {{ formatPrice(product.price) ?? CONTENT.products.priceOnRequest }}
      </span>
      <button
        type="button"
        class="flex h-10 items-center gap-1 bg-navy px-3 text-xs font-medium text-white
          transition duration-300 hover:bg-gold"
        :aria-label="`${CONTENT.products.add}: ${product.name}`"
        @click="addToCart"
      >
        <component :is="selected ? Check : Plus" :size="14" aria-hidden="true" />
        {{ selected ? CONTENT.shop.inCart : CONTENT.products.add }}
      </button>
    </div>

    <!-- Signature gold accent: grows from the start edge on hover -->
    <span
      class="pointer-events-none absolute inset-x-0 bottom-0 h-1 origin-right scale-x-[.18]
        bg-gold transition-transform duration-500 group-hover:scale-x-100"
    />
  </article>
</template>
