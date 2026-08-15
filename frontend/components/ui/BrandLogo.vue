<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

// Horizontal wordmark rendered as a CSS mask tinted with a single fill, so one
// SVG serves every surface. Brand gold by default (reads on navy and on light);
// pass `color` to override.
const props = withDefaults(
  defineProps<{ height?: number; color?: string }>(),
  { height: 28, color: '#B08A57' },
)

const RATIO = 193.02 / 70 // logo viewBox aspect
const style = computed(() => {
  const url = 'url(/logo-horizontal.svg)'
  return {
    height: `${props.height}px`,
    width: `${Math.round(props.height * RATIO)}px`,
    backgroundColor: props.color,
    maskImage: url,
    WebkitMaskImage: url,
    maskRepeat: 'no-repeat',
    WebkitMaskRepeat: 'no-repeat',
    maskSize: 'contain',
    WebkitMaskSize: 'contain',
    maskPosition: 'center',
    WebkitMaskPosition: 'center',
  }
})
</script>

<template>
  <span class="inline-block shrink-0" :style="style" role="img" :aria-label="CONTENT.brand" />
</template>
