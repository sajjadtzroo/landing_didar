<script setup lang="ts">
import { CONTENT } from '~/constants/content'

defineEmits<{ order: [] }>()

// Signature moment: muted looping video, swapped for a static image under
// reduced-motion. Per-landing video/poster come in as props; fall back to the
// bundled default so a landing with no video set never renders a broken <video>.
const props = withDefaults(
  defineProps<{ videoUrl?: string; posterUrl?: string }>(),
  { videoUrl: '/media/hero.mp4', posterUrl: '/media/hero-poster.jpg' },
)
const heroVideo = computed(() => props.videoUrl)
const heroPoster = computed(() => props.posterUrl)
const reduced = import.meta.client
  ? useMediaQuery('(prefers-reduced-motion: reduce)')
  : ref(false)
</script>

<template>
  <section class="relative flex min-h-[100svh] items-center justify-center overflow-hidden">
    <!-- Full-bleed media -->
    <div class="absolute inset-0 bg-media-surface">
      <video
        v-if="!reduced"
        class="h-full w-full object-cover"
        autoplay
        muted
        loop
        playsinline
        :poster="heroPoster"
      >
        <source :src="heroVideo" type="video/mp4" />
      </video>
      <NuxtImg
        v-else
        :src="heroPoster"
        alt=""
        class="h-full w-full object-cover"
        width="1450"
        height="1000"
      />
      <!-- Layered navy reveal (RTL-aware) so the type stays legible over the piece -->
      <div class="absolute inset-0 bg-navy/[0.55]" />
      <div class="absolute inset-0 bg-gradient-to-l from-navy via-navy/80 to-navy/25" />
      <div class="absolute inset-0 bg-gradient-to-t from-navy-deep/80 via-transparent to-navy/30" />
    </div>

    <div class="relative mx-auto w-full max-w-hero px-6 text-start text-cream sm:px-10">
      <BrandLogo :height="52" color="#F7F3EE" class="mb-8" />
      <p class="mb-4 text-xs uppercase tracking-[0.24em] text-gold-soft sm:text-sm">
        {{ CONTENT.hero.eyebrow }}
      </p>
      <h1
        class="max-w-2xl text-balance text-[44px] font-medium leading-[1.18]
          sm:text-[60px] lg:text-[72px]"
      >
        {{ CONTENT.hero.headline }}
      </h1>
      <p
        class="mt-5 max-w-md text-pretty text-base leading-[1.75] text-cream/80
          sm:mt-6 sm:max-w-xl sm:text-lg"
      >
        {{ CONTENT.hero.supporting }}
      </p>
      <button
        type="button"
        class="mt-9 inline-flex h-[58px] w-[220px] items-center justify-center bg-gold
          text-base font-medium text-white transition duration-300 hover:-translate-y-1
          hover:bg-navy"
        @click="$emit('order')"
      >
        {{ CONTENT.hero.cta }}
      </button>
    </div>
  </section>
</template>
