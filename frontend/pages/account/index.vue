<script setup lang="ts">
import { ChevronLeft } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { OrderTrack, Product } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ middleware: 'customer' })

const orders = ref<OrderTrack[]>([])
const favorites = ref<Product[]>([])

onMounted(async () => {
  const [o, f] = await Promise.all([
    apiFetch<OrderTrack[]>('/account/me/orders').catch(() => []),
    apiFetch<Product[]>('/account/me/favorites').catch(() => []),
  ])
  orders.value = o
  favorites.value = f
})

useHead({ title: `${CONTENT.account.tabs.overview} | ${CONTENT.brand}` })
</script>

<template>
  <AccountShell v-slot="{ customer }">
    <h2 class="text-xl text-ink">{{ CONTENT.account.greeting(customer?.full_name || '') }}</h2>

    <div class="mt-6 grid grid-cols-2 gap-4">
      <NuxtLink to="/account/orders" class="border border-line bg-surface-raised p-5 transition hover:border-navy">
        <p class="text-sm text-ink-muted">{{ CONTENT.account.ordersCount }}</p>
        <p class="tnum mt-1 text-3xl font-bold text-ink">{{ toFa(orders.length) }}</p>
      </NuxtLink>
      <NuxtLink to="/account/favorites" class="border border-line bg-surface-raised p-5 transition hover:border-navy">
        <p class="text-sm text-ink-muted">{{ CONTENT.account.favoritesCount }}</p>
        <p class="tnum mt-1 text-3xl font-bold text-ink">{{ toFa(favorites.length) }}</p>
      </NuxtLink>
    </div>

    <!-- Last order -->
    <div v-if="orders.length" class="mt-8">
      <div class="mb-3 flex items-center justify-between">
        <h3 class="text-sm font-medium text-ink">{{ CONTENT.account.lastOrder }}</h3>
        <NuxtLink to="/account/orders" class="flex items-center gap-1 text-sm text-gold-text">
          {{ CONTENT.account.viewAll }} <ChevronLeft :size="14" />
        </NuxtLink>
      </div>
      <div class="flex items-center justify-between border border-line bg-surface-raised p-4">
        <span class="tnum font-bold tracking-wider text-gold-text" dir="ltr">{{ orders[0].reference }}</span>
        <span class="bg-navy px-3 py-1 text-sm text-white">
          {{ CONTENT.orderStatuses[orders[0].status] }}
        </span>
      </div>
    </div>
  </AccountShell>
</template>
