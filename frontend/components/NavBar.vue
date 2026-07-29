<script setup lang="ts">
import { computed } from 'vue'
import { CONTENT } from '~/constants/content'

defineEmits<{ order: [] }>()

const route = useRoute()
const { y } = import.meta.client ? useWindowScroll() : { y: ref(0) }

// Transparent (light text) only while sitting over the dark hero on the home page;
// frosted glass (dark text) after scrolling, and on every inner page.
const overHero = computed(() => route.path === '/' && y.value < 80)
</script>

<template>
  <header
    class="chrome-blur fixed inset-x-0 top-0 z-40 transition-colors duration-300"
    :class="
      overHero
        ? 'bg-transparent text-cream'
        : 'border-b border-line bg-surface/70 text-ink backdrop-blur-xl backdrop-saturate-150'
    "
  >
    <!-- Legibility scrim over the hero (only in the transparent state) -->
    <div
      v-if="overHero"
      class="pointer-events-none absolute inset-0 bg-gradient-to-b from-navy-deep/50 to-transparent"
      aria-hidden="true"
    />

    <nav
      class="relative mx-auto flex max-w-content items-center justify-between px-5 py-3 sm:px-10"
      aria-label="اصلی"
    >
      <!-- Brand -->
      <NuxtLink to="/" class="flex items-center" :aria-label="`${CONTENT.brand} — خانه`">
        <BrandLogo :height="26" />
      </NuxtLink>

      <!-- Actions -->
      <div class="flex items-center gap-2 sm:gap-4">
        <button
          type="button"
          class="flex h-11 items-center justify-center bg-navy px-5 text-sm font-medium
            text-white transition duration-300 hover:bg-gold"
          @click="$emit('order')"
        >
          {{ CONTENT.nav.order }}
        </button>
      </div>
    </nav>
  </header>
</template>
