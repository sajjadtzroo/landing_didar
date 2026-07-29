<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import { CONTENT } from '~/constants/content'
import { formatPrice } from '~/utils/format'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; continue: [] }>()

const cart = useCartStore()
const { trackEvent } = useAnalytics()

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
          <p class="tnum mt-1 text-sm text-gold-text">
            {{ formatPrice(item.price) ?? CONTENT.products.priceOnRequest }}
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
        <span class="tnum font-medium text-gold-text">
          {{ formatPrice(cart.total) ?? CONTENT.products.priceOnRequest }}
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
