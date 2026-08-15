<script setup lang="ts">
defineProps<{ title: string; eyebrow?: string; description?: string }>()
</script>

<template>
  <div class="mb-12 text-center">
    <p
      v-if="eyebrow"
      class="mb-4 text-xs tracking-[0.25em] text-gold-text sm:text-sm"
    >
      {{ eyebrow }}
    </p>
    <h2 class="text-4xl font-normal leading-[1.55] text-ink sm:text-5xl">{{ title }}</h2>
    <!-- Signature motif: gold hairline + ✦ -->
    <div class="divider-star">✦</div>
    <p
      v-if="description"
      class="mx-auto mt-5 max-w-3xl text-base leading-8 text-ink-muted sm:text-lg sm:leading-9"
    >
      {{ description }}
    </p>
  </div>
</template>
