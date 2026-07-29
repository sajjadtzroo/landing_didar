<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

// Monochrome horizontal wordmark rendered as a CSS mask tinted with currentColor,
// so it adapts to context (cream over the hero, ink when the navbar frosts, cream
// on the navy footer) without needing separate light/dark logo files.
const props = withDefaults(defineProps<{ height?: number }>(), { height: 28 })

const RATIO = 193.02 / 70 // logo viewBox aspect
const style = computed(() => {
  const url = 'url(/logo-horizontal.svg)'
  return {
    height: `${props.height}px`,
    width: `${Math.round(props.height * RATIO)}px`,
    backgroundColor: 'currentColor',
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
