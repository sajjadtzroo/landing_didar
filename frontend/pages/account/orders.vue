<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { OrderTrack } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

definePageMeta({ middleware: 'customer' })

const orders = ref<OrderTrack[]>([])
const loading = ref(true)

onMounted(async () => {
  orders.value = await apiFetch<OrderTrack[]>('/account/me/orders').catch(() => [])
  loading.value = false
})

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('fa-IR'))
}

useHead({ title: `${CONTENT.account.ordersTitle} | ${CONTENT.brand}` })
</script>

<template>
  <AccountShell>
    <h2 class="mb-6 text-xl text-ink">{{ CONTENT.account.ordersTitle }}</h2>

    <div v-if="loading" class="py-10 text-center text-ink-muted">…</div>

    <div v-else-if="!orders.length" class="border border-line bg-surface-raised py-16 text-center">
      <p class="text-ink-muted">{{ CONTENT.account.ordersEmpty }}</p>
      <NuxtLink to="/shop" class="mt-4 inline-flex h-11 items-center bg-navy px-5 text-sm text-white hover:bg-gold">
        {{ CONTENT.account.goShop }}
      </NuxtLink>
    </div>

    <ul v-else class="space-y-5">
      <li v-for="o in orders" :key="o.reference" class="border border-line bg-surface-raised p-5">
        <div class="flex items-center justify-between border-b border-line pb-3">
          <div>
            <span class="tnum font-bold tracking-wider text-gold-text" dir="ltr">{{ o.reference }}</span>
            <span class="ms-3 text-xs text-ink-muted">{{ CONTENT.account.orderedOn }}: {{ faDate(o.created_at) }}</span>
          </div>
          <span class="bg-navy px-3 py-1 text-sm text-white">{{ CONTENT.orderStatuses[o.status] }}</span>
        </div>

        <ul class="mt-3 space-y-1 text-sm text-ink">
          <li v-for="(it, i) in o.items" :key="i" class="flex justify-between">
            <span>{{ it.product_name }} × {{ toFa(it.quantity) }}</span>
            <span class="tnum text-gold-text">
              {{ formatPrice(it.unit_price) ?? CONTENT.products.priceOnRequest }}
            </span>
          </li>
        </ul>

        <ol class="mt-4 flex flex-wrap gap-x-6 gap-y-1 border-t border-line pt-3 text-xs text-ink-muted">
          <li v-for="(s, i) in o.status_log" :key="i" class="flex items-center gap-1">
            <span class="h-1.5 w-1.5 rounded-full bg-gold" aria-hidden="true" />
            {{ CONTENT.orderStatuses[s.to_status] }}
          </li>
        </ol>
      </li>
    </ul>
  </AccountShell>
</template>
