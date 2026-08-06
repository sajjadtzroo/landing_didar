<script setup lang="ts">
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { OrderTrack } from '~/types'
import { formatPrice, toFa } from '~/utils/format'

// Account-less order tracking: reference + phone must both match (server-enforced).
const reference = ref('')
const phone = ref('')
const loading = ref(false)
const error = ref('')
const order = ref<OrderTrack | null>(null)

async function lookup() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  order.value = null
  try {
    order.value = await apiFetch<OrderTrack>('/orders/track', {
      query: { reference: reference.value.trim(), phone: phone.value.trim() },
    })
  } catch (e: unknown) {
    const status = (e as { statusCode?: number; response?: { status?: number } })
    error.value = (status.statusCode === 404 || status.response?.status === 404)
      ? CONTENT.track.notFound
      : CONTENT.track.generic
  } finally {
    loading.value = false
  }
}

useHead({
  title: `${CONTENT.track.title} | ${CONTENT.brand}`,
  meta: [{ name: 'description', content: CONTENT.track.description }],
})
</script>

<template>
  <main class="pt-32 sm:pt-28">
    <div class="mx-auto max-w-xl px-5 pb-16 sm:px-10">
      <h1 class="text-3xl font-medium text-ink sm:text-4xl">{{ CONTENT.track.title }}</h1>
      <p class="mt-3 text-base leading-8 text-ink-muted">{{ CONTENT.track.description }}</p>

      <form class="mt-8 space-y-5" novalidate @submit.prevent="lookup">
        <FormField :label="CONTENT.track.reference" v-slot="{ id }">
          <input
            :id="id"
            v-model="reference"
            type="text"
            dir="ltr"
            class="form-control text-start"
            :placeholder="CONTENT.track.referencePlaceholder"
            autocomplete="off"
          />
        </FormField>
        <FormField :label="CONTENT.track.phone" v-slot="{ id }">
          <input
            :id="id"
            v-model="phone"
            type="tel"
            inputmode="numeric"
            dir="ltr"
            class="form-control text-start"
            autocomplete="tel"
          />
        </FormField>
        <button
          type="submit"
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium
            text-white transition duration-300 hover:bg-gold disabled:opacity-60"
          :disabled="loading || !reference || !phone"
        >
          {{ loading ? CONTENT.track.submitting : CONTENT.track.submit }}
        </button>
      </form>

      <p v-if="error" role="alert" class="mt-6 border border-danger bg-danger-soft p-3 text-sm text-danger">
        {{ error }}
      </p>

      <!-- Result -->
      <section v-if="order" class="mt-10 border border-line bg-surface-raised p-5">
        <div class="flex items-center justify-between border-b border-line pb-4">
          <div>
            <p class="text-sm text-ink-muted">{{ CONTENT.success.reference }}</p>
            <p class="tnum text-xl font-bold tracking-wider text-gold-text" dir="ltr">{{ order.reference }}</p>
          </div>
          <span class="bg-navy px-3 py-1 text-sm font-medium text-white">
            {{ CONTENT.track.statuses[order.status] }}
          </span>
        </div>

        <!-- Items -->
        <p class="mt-5 mb-2 text-sm font-medium text-ink">{{ CONTENT.track.items }}</p>
        <ul class="space-y-1 text-sm text-ink">
          <li v-for="(it, i) in order.items" :key="i" class="flex justify-between">
            <span>{{ it.product_name }} × {{ toFa(it.quantity) }}</span>
            <span class="tnum text-gold-text">
              {{ formatPrice(it.unit_price) ?? CONTENT.products.priceOnRequest }}
            </span>
          </li>
        </ul>

        <!-- Timeline -->
        <p class="mt-6 mb-3 text-sm font-medium text-ink">{{ CONTENT.track.timeline }}</p>
        <ol class="space-y-3 border-s border-line ps-4">
          <li v-for="(s, i) in order.status_log" :key="i" class="relative">
            <span class="absolute -start-[21px] top-1 h-2.5 w-2.5 rounded-full bg-gold" aria-hidden="true" />
            <span class="text-sm text-ink">{{ CONTENT.track.statuses[s.to_status] }}</span>
          </li>
        </ol>
      </section>
    </div>
  </main>
</template>
