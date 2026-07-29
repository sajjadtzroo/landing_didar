<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

defineEmits<{ order: [] }>()

// Appears after 200px of scroll (brief). Translucent chrome (apple-design §12).
const { y } = import.meta.client ? useWindowScroll() : { y: ref(0) }
const show = computed(() => y.value > 200)
</script>

<template>
  <Transition name="fade-down">
    <header
      v-show="show"
      class="chrome-blur fixed inset-x-0 top-0 z-40 border-b border-line bg-header
        backdrop-blur-md backdrop-saturate-150"
    >
      <div class="mx-auto flex max-w-content items-center justify-between px-5 py-3 sm:px-10">
        <span class="text-lg font-medium tracking-tight text-ink">{{ CONTENT.brand }}</span>
        <button
          type="button"
          class="flex h-11 items-center justify-center bg-navy px-6 text-sm font-medium
            text-white transition duration-300 hover:bg-gold"
          @click="$emit('order')"
        >
          {{ CONTENT.nav.order }}
        </button>
      </div>
    </header>
  </Transition>
</template>

<style scoped>
.fade-down-enter-active,
.fade-down-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-down-enter-from,
.fade-down-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}
</style>
