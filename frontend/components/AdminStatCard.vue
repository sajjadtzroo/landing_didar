<script setup lang="ts">
import type { Component } from 'vue'

// KPI tile: gold icon badge + label + tabular value. Used on the dashboard grid.
defineProps<{ label: string; value: string | number; icon?: Component }>()
</script>

<template>
  <div class="admin-card admin-card--hover flex items-center gap-3 p-4">
    <span
      v-if="icon"
      class="corner-soft flex h-11 w-11 shrink-0 items-center justify-center bg-gradient-to-br
        from-gold/25 to-gold-soft/10 text-gold-text ring-1 ring-inset ring-white/50"
      aria-hidden="true"
    >
      <component :is="icon" :size="20" :stroke-width="1.75" />
    </span>
    <div class="min-w-0">
      <p class="truncate text-xs text-ink-muted">{{ label }}</p>
      <p class="tnum mt-1 text-xl font-medium text-gold-text">{{ value }}</p>
    </div>
  </div>
</template>
