<script setup lang="ts">
import { Minus, Plus } from 'lucide-vue-next'
import { toFa } from '~/utils/format'

const props = defineProps<{ modelValue: number; min?: number }>()
const emit = defineEmits<{ 'update:modelValue': [number] }>()

const min = props.min ?? 1
function set(v: number) {
  emit('update:modelValue', Math.max(min, v))
}
</script>

<template>
  <div class="inline-flex items-center border border-line">
    <button
      type="button"
      class="flex h-11 w-11 items-center justify-center text-ink hover:text-gold-text
        disabled:text-ink-muted"
      :disabled="modelValue <= min"
      aria-label="کاهش تعداد"
      @click="set(modelValue - 1)"
    >
      <Minus :size="18" />
    </button>
    <span class="tnum w-10 text-center text-ink">{{ toFa(modelValue) }}</span>
    <button
      type="button"
      class="flex h-11 w-11 items-center justify-center text-ink hover:text-gold-text"
      aria-label="افزایش تعداد"
      @click="set(modelValue + 1)"
    >
      <Plus :size="18" />
    </button>
  </div>
</template>
