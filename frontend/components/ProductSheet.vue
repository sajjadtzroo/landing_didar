<script setup lang="ts">
import { ref, watch } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

const props = defineProps<{ modelValue: boolean; product: Product | null }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const cart = useCartStore()
const { trackEvent, addEcommerceItem, trackEcommerceCartUpdate } = useAnalytics()

const qty = ref(1)
const imageEl = ref<HTMLElement | null>(null)
watch(
  () => props.modelValue,
  (open) => {
    if (open) qty.value = 1
  },
)

function add() {
  if (!props.product) return
  cart.addItem(props.product, qty.value)
  flyToCart(imageEl.value, props.product.image_url)
  trackEvent('cart', 'add', props.product.name, qty.value)
  // Ecommerce: mirror the whole cart so abandoned-cart reports are accurate.
  syncEcommerceCart()
  emit('update:modelValue', false)
}

function syncEcommerceCart() {
  for (const i of cart.items) {
    addEcommerceItem(i.sku, i.name, 'jewelry', i.price ?? 0, i.quantity)
  }
  trackEcommerceCartUpdate(cart.total)
}
</script>

<template>
  <BaseSheet
    :model-value="modelValue"
    :title="product?.name"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template v-if="product">
      <div ref="imageEl" class="aspect-square w-full overflow-hidden bg-media-surface">
        <NuxtImg
          v-if="product.image_url"
          :src="product.image_url"
          :alt="product.name"
          class="h-full w-full object-cover"
          width="600"
          height="600"
        />
      </div>

      <dl class="mt-5 grid grid-cols-2 gap-y-3 text-sm">
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

      <p v-if="product.description" class="mt-4 text-sm leading-7 text-ink-muted">
        {{ product.description }}
      </p>

      <p class="tnum mt-5 text-lg text-gold-text">
        {{ formatPrice(product.price) ?? CONTENT.products.priceOnRequest }}
      </p>
    </template>

    <template #footer>
      <div class="flex items-center justify-between gap-4">
        <QtyStepper v-model="qty" />
        <button
          type="button"
          class="flex h-[58px] flex-1 items-center justify-center bg-navy text-base
            font-medium text-white transition duration-300 hover:bg-gold"
          @click="add"
        >
          {{ CONTENT.products.add }}
        </button>
      </div>
    </template>
  </BaseSheet>
</template>
