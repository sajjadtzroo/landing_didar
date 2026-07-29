<script setup lang="ts">
import { CONTENT } from '~/constants/content'

// Global storefront chrome — nav, footer, cart + order overlays — so they appear
// on the landing and every product page. Admin pages use layout: 'admin'.
const { cartOpen, orderOpen, successRef, openCart, openOrder, onOrderSuccess } =
  useUiState()
</script>

<template>
  <div>
    <NavBar @order="openOrder" />
    <TubelightNav />

    <slot />

    <ContactFooter id="footer" />

    <!-- Floating cart + drawer -->
    <CartBubble @open="openCart" />
    <CartDrawer v-model="cartOpen" @continue="openOrder" />

    <!-- Order form sheet -->
    <BaseSheet v-model="orderOpen" :title="CONTENT.form.title">
      <OrderForm @success="onOrderSuccess" />
    </BaseSheet>

    <!-- Success overlay -->
    <SuccessScreen v-if="successRef" :reference="successRef" />
  </div>
</template>
