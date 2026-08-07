<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CONTENT } from '~/constants/content'

definePageMeta({ middleware: 'customer' })

const { store, syncOnLogin } = useFavorites()
const loading = ref(true)
const search = ref('')

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return store.items
  return store.items.filter(
    (p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q),
  )
})

onMounted(async () => {
  await syncOnLogin() // pull the server list into the store (union with local)
  loading.value = false
})

useHead({ title: `${CONTENT.account.favoritesTitle} | ${CONTENT.brand}` })
</script>

<template>
  <AccountShell>
    <h2 class="mb-6 text-xl text-ink">{{ CONTENT.account.favoritesTitle }}</h2>

    <div v-if="loading" class="py-10 text-center text-ink-muted">…</div>

    <p v-else-if="!store.items.length" class="border border-line bg-surface-raised py-16 text-center text-ink-muted">
      {{ CONTENT.account.favoritesEmpty }}
    </p>

    <template v-else>
      <input
        v-model="search"
        type="search"
        :placeholder="CONTENT.shop.searchPlaceholder"
        class="form-control mb-6 sm:max-w-xs"
        aria-label="جستجو"
      />
      <div v-if="filtered.length" class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-3">
        <ProductCard v-for="(p, i) in filtered" :key="p.id" :product="p" :index="i" shop />
      </div>
      <p v-else class="py-16 text-center text-ink-muted">{{ CONTENT.shop.noMatch }}</p>
    </template>
  </AccountShell>
</template>
