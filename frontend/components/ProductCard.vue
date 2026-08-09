<script setup lang="ts">
import { Check, Heart, Plus } from 'lucide-vue-next'
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'
import { toFa } from '~/utils/format'

// `shop` mode (storefront /shop) adds a favorite heart + add-to-cart button.
// No price anywhere (wholesale gold — the value shown is weight + عیار + اجرت).
const props = defineProps<{ product: Product; index: number; shop?: boolean }>()

const cart = useCartStore()
const { openCart } = useUiState()
const { toast } = useToast()
const { isFav, toggle } = useFavorites()
const selected = computed(() => cart.isSelected(props.product.id))
const qty = computed(() => cart.quantityOf(props.product.id))
// Sample pieces (نمونه) are shown for reference but can't be ordered.
const isSample = computed(() => props.product.product_status === 'sample')

// Second gallery image (if imported) → crossfade on hover.
const hoverImage = computed(() => {
  const imgs = props.product.images || []
  const second = imgs.find((u) => u && u !== props.product.image_url)
  return second ?? null
})

function addToCart() {
  cart.addItem(props.product)
  toast(CONTENT.cart.addedToast)
  openCart()
}

// Favorites work for guests (persisted locally) and sync on login.
async function onHeart() {
  const added = await toggle(props.product)
  toast(added ? CONTENT.account.favAddedToast : CONTENT.account.favRemovedToast)
}
</script>

<template>
  <article
    class="corner-soft group relative cursor-pointer overflow-hidden border border-line
      bg-surface-raised transition duration-300 hover:-translate-y-2 hover:shadow-xl"
  >
    <!-- Favorite heart (shop only). Sibling of the link so it never navigates. -->
    <button
      v-if="shop"
      type="button"
      class="absolute start-2 top-2 z-10 flex h-11 w-11 items-center justify-center rounded-full
        bg-surface/80 backdrop-blur transition hover:bg-surface"
      :aria-label="CONTENT.account.favoritesTitle"
      :aria-pressed="isFav(product.id)"
      @click="onHeart"
    >
      <Heart
        :size="18"
        :class="isFav(product.id) ? 'fill-danger text-danger' : 'text-ink-muted'"
        aria-hidden="true"
      />
    </button>

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
          sizes="(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 320px"
          :loading="index < 4 ? 'eager' : 'lazy'"
          :fetchpriority="index === 0 ? 'high' : undefined"
        />
        <!-- Second gallery image: crossfades in on hover -->
        <NuxtImg
          v-if="product.image_url && hoverImage"
          :src="hoverImage"
          :alt="product.name"
          class="absolute inset-0 h-full w-full object-cover opacity-0 transition-opacity
            duration-500 group-hover:opacity-100"
          width="400"
          height="400"
          format="webp"
          sizes="(max-width: 640px) 45vw, (max-width: 1024px) 30vw, 320px"
          loading="lazy"
          aria-hidden="true"
        />
        <!-- Fallback when a product has no imagery yet -->
        <div
          v-if="!product.image_url"
          class="flex h-full w-full items-center justify-center"
          aria-hidden="true"
        >
          <BrandLogo :height="34" color="#D9B985" />
        </div>

        <!-- Selected · qty state (icon+text, never colour-only) -->
        <span
          v-if="selected"
          class="absolute end-2 top-2 flex items-center gap-1 bg-navy px-2 py-1 text-xs
            font-medium text-white"
        >
          ✓ {{ CONTENT.products.added }} · {{ toFa(qty) }}
        </span>
        <!-- Sample badge -->
        <span
          v-else-if="isSample"
          class="absolute end-2 top-2 bg-ink/85 px-2 py-1 text-xs font-medium text-white"
        >
          {{ CONTENT.products.sample }}
        </span>
      </div>

      <div class="px-4 py-4">
        <h3 class="text-lg text-ink">{{ product.name }}</h3>
        <p class="mt-1 text-sm text-ink-muted">
          {{ CONTENT.products.sku }} {{ product.sku }}
        </p>
        <!-- Value row: weight leads (wholesale signal), then عیار + اجرت -->
        <p
          v-if="product.weight_grams || product.karat || product.ojrat_percent"
          class="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm"
        >
          <span v-if="product.weight_grams" class="tnum font-medium text-gold-text">
            {{ toFa(Number(product.weight_grams)) }} {{ CONTENT.products.gram }}
          </span>
          <span v-if="product.karat" class="tnum text-ink-muted">
            · {{ CONTENT.products.karat }} {{ toFa(product.karat) }}
          </span>
          <span v-if="product.ojrat_percent" class="tnum text-ink-muted">
            · {{ CONTENT.products.ojrat }} {{ toFa(Number(product.ojrat_percent)) }}٪
          </span>
        </p>
      </div>
    </NuxtLink>

    <!-- Shop mode: add-to-cart (OUTSIDE the link so tapping add doesn't navigate).
         Mobile → 44px circle; desktop → full-width bar for clear affordance. -->
    <div v-if="shop" class="px-4 pb-4">
      <p
        v-if="isSample"
        class="corner-soft border border-line py-2.5 text-center text-sm text-ink-muted"
      >
        {{ CONTENT.products.sampleNote }}
      </p>
      <template v-else>
        <button
          type="button"
          class="ms-auto flex h-11 w-11 items-center justify-center rounded-full text-white
            transition duration-300 active:scale-95 sm:hidden"
          :class="selected ? 'bg-gold' : 'bg-navy hover:bg-gold'"
          :aria-label="selected ? CONTENT.shop.inCart : `${CONTENT.products.add}: ${product.name}`"
          @click="addToCart"
        >
          <component :is="selected ? Check : Plus" :size="20" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="hidden h-11 w-full items-center justify-center gap-2 text-sm font-medium text-white
            transition duration-300 active:scale-[0.98] sm:flex"
          :class="selected ? 'bg-gold' : 'bg-navy hover:bg-gold'"
          :aria-label="selected ? CONTENT.shop.inCart : `${CONTENT.products.add}: ${product.name}`"
          @click="addToCart"
        >
          <component :is="selected ? Check : Plus" :size="18" aria-hidden="true" />
          {{ selected ? CONTENT.shop.inCart : CONTENT.shop.addToCart }}
        </button>
      </template>
    </div>

    <!-- Signature gold accent: grows from the start edge on hover -->
    <span
      class="pointer-events-none absolute inset-x-0 bottom-0 h-1 origin-right scale-x-[.18]
        bg-gold transition-transform duration-500 group-hover:scale-x-100"
    />
  </article>
</template>
