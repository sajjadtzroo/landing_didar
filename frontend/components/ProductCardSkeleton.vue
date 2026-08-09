<script setup lang="ts">
// Placeholder tile shown while the catalogue loads — mirrors ProductCard's shape
// so the grid doesn't reflow when data arrives. Pure-CSS shimmer, reduced-motion
// aware (no library).
</script>

<template>
  <div class="corner-soft overflow-hidden border border-line bg-surface-raised">
    <div class="sk aspect-square" />
    <div class="space-y-2 px-4 py-4">
      <div class="sk h-4 w-2/3" />
      <div class="sk h-3 w-1/3" />
      <div class="sk mt-3 h-4 w-1/2" />
      <div class="sk mt-3 h-11 w-full" />
    </div>
  </div>
</template>

<style scoped>
.sk {
  position: relative;
  overflow: hidden;
  background: var(--surface-soft);
}
.sk::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(100%);
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.55),
    transparent
  );
  animation: sk-shimmer 1.4s ease-in-out infinite;
}
@keyframes sk-shimmer {
  100% {
    transform: translateX(-100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .sk::after {
    animation: none;
  }
}
</style>
