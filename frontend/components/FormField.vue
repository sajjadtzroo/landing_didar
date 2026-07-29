<script setup lang="ts">
import { useId } from 'vue'

defineProps<{ label: string; error?: string; required?: boolean }>()
const id = useId()
</script>

<template>
  <div>
    <label :for="id" class="mb-2 block text-sm text-ink">
      {{ label }}
      <span v-if="required" class="text-danger" aria-hidden="true">*</span>
    </label>
    <slot :id="id" />
    <p
      v-if="error"
      :id="`${id}-error`"
      role="alert"
      class="mt-1.5 text-xs text-danger"
    >
      {{ error }}
    </p>
  </div>
</template>
