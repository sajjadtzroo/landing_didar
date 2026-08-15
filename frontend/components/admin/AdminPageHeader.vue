<script setup lang="ts">
// Unified admin section header: title + gold accent rule, optional subtitle,
// and a trailing slot for page actions (add / export / filters).
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
    <div>
      <h1 class="flex items-center gap-3 text-2xl font-medium text-ink">
        <span class="h-6 w-1 bg-gold" aria-hidden="true" />
        {{ title }}
      </h1>
      <p v-if="subtitle" class="mt-1.5 ps-4 text-sm text-ink-muted">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-3">
      <slot />
    </div>
  </div>
</template>
