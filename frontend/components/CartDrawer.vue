<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import { computed, watchEffect } from 'vue'
import { CONTENT } from '~/constants/content'
import type { Product } from '~/types'
import { formatGrams, toFa } from '~/utils/format'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; continue: [] }>()

const cart = useCartStore()
const { trackEvent } = useAnalytics()

// Backfill weight data onto cart items from the live catalog — items persisted
// before weight_display existed (localStorage) otherwise show the old midpoint.
// Reuses the shared 'products' fetch (cached) so it's ~free on shop pages.
const { data: products } = useFetch<Product[]>('/products', {
  baseURL: useApiBase(),
  key: 'products',
  default: () => [],
})
watchEffect(() => {
  if (products.value?.length) cart.syncWeights(products.value)
})

// Grand total as a weight range («۲۴-۳۰ گرم») when any piece varies; a plain
// number when every item has a single weight.
const totalWeightLabel = computed(() => {
  const { min, max } = cart.totalWeightRange
  if (min === 0 && max === 0) return null
  if (min === max) return formatGrams(min)
  return `${toFa(min.toLocaleString('en-US', { maximumFractionDigits: 2 }))}-${toFa(
    max.toLocaleString('en-US', { maximumFractionDigits: 2 }),
  )} گرم`
})

function remove(productId: string, name: string) {
  cart.removeItem(productId)
  trackEvent('cart', 'remove', name)
}
</script>

<template>
  <BaseSheet
    :model-value="props.modelValue"
    :title="CONTENT.cart.title"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p v-if="!cart.items.length" class="py-10 text-center text-ink-muted">
      {{ CONTENT.cart.empty }}
    </p>

    <ul v-else class="divide-y divide-line">
      <li v-for="item in cart.items" :key="item.productId" class="flex gap-4 py-4">
        <div class="h-20 w-20 shrink-0 overflow-hidden bg-media-surface">
          <NuxtImg
            v-if="item.imageUrl"
            :src="item.imageUrl"
            :alt="item.name"
            class="h-full w-full object-cover"
            width="80"
            height="80"
          />
        </div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-ink">{{ item.name }}</p>
          <p class="mt-1 text-sm text-gold-text">
            {{
              item.weightDisplay
                ? toFa(item.weightDisplay)
                : (formatGrams(item.weightGrams) ?? CONTENT.products.priceOnRequest)
            }}
          </p>
          <div class="mt-2 flex items-center gap-3">
            <QtyStepper
              :model-value="item.quantity"
              @update:model-value="cart.updateQuantity(item.productId, $event)"
            />
            <button
              type="button"
              class="flex h-11 w-11 items-center justify-center text-ink-muted hover:text-danger"
              :aria-label="`${CONTENT.cart.remove}: ${item.name}`"
              @click="remove(item.productId, item.name)"
            >
              <Trash2 :size="18" />
            </button>
          </div>
        </div>
      </li>
    </ul>

    <template v-if="cart.items.length" #footer>
      <div class="mb-4 flex items-center justify-between text-ink">
        <span>{{ CONTENT.cart.total }}</span>
        <span class="font-medium text-gold-text">
          {{ totalWeightLabel ?? CONTENT.products.priceOnRequest }}
        </span>
      </div>
      <button
        type="button"
        class="flex h-[58px] w-full items-center justify-center bg-navy text-base
          font-medium text-white transition duration-300 hover:bg-gold"
        @click="emit('continue')"
      >
        {{ CONTENT.cart.continue }}
      </button>
    </template>
  </BaseSheet>
</template>
