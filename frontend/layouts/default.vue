<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

// Global storefront chrome. One nav per context: the landing (/l/*) uses the
// bottom tubelight pill; storefront pages (/products, …) use the top glass navbar.
const { cartOpen, orderOpen, successRef, openCart, openOrder, onOrderSuccess } =
  useUiState()
const route = useRoute()
const isLanding = computed(() => route.path.startsWith('/l'))
</script>

<template>
  <div>
    <NavBar v-if="!isLanding" @order="openOrder" />
    <template v-if="isLanding">
      <TubelightNav />
      <CartFab @open="openCart" />
    </template>

    <slot />

    <ContactFooter id="footer" />

    <!-- Cart lives inside the TubelightNav pill now (no separate floating bubble). -->
    <CartDrawer v-model="cartOpen" @continue="openOrder" />

    <!-- Order form sheet -->
    <BaseSheet v-model="orderOpen" :title="CONTENT.form.title">
      <OrderForm @success="onOrderSuccess" />
    </BaseSheet>

    <!-- Success overlay -->
    <SuccessScreen v-if="successRef" :reference="successRef" />
  </div>
</template>
