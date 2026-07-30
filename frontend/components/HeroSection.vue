<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
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

// The poster is the LCP element. Defer the video's download until the page is
// idle so a heavy hero file never competes with first paint (helps mobile LCP
// regardless of the video's size). Muted autoplay resumes once the source lands.
const videoEl = ref<HTMLVideoElement | null>(null)
const showVideo = ref(false)
onMounted(() => {
  const start = () => (showVideo.value = true)
  if ('requestIdleCallback' in window) requestIdleCallback(start, { timeout: 2000 })
  else setTimeout(start, 1200)
})
watch(showVideo, async (on) => {
  if (on) {
    await nextTick()
    videoEl.value?.load()
  }
})
</script>

<template>
  <section class="relative flex min-h-[100svh] items-center justify-center overflow-hidden">
    <!-- Full-bleed media -->
    <div class="absolute inset-0 bg-media-surface">
      <video
        v-if="!reduced"
        ref="videoEl"
        class="h-full w-full object-cover"
        autoplay
        muted
        loop
        playsinline
        preload="none"
        :poster="heroPoster"
      >
        <source v-if="showVideo" :src="heroVideo" type="video/mp4" />
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
      <h1
        class="max-w-2xl text-[44px] font-medium leading-[1.18]
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
      <!-- Primary CTA: sharp-cornered to match brand; gold fill + navy text (AA),
           a gold-soft sweep and a leading arrow that advances on hover/focus. -->
      <button
        type="button"
        class="group relative mt-9 inline-flex h-[60px] items-center gap-3 overflow-hidden
          bg-gold px-8 text-base font-semibold text-navy
          shadow-[0_12px_30px_-10px_rgba(176,138,87,0.65)]
          transition-[transform,box-shadow] duration-300 ease-out
          hover:-translate-y-0.5 hover:shadow-[0_18px_44px_-12px_rgba(176,138,87,0.8)]
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2
          focus-visible:outline-cream motion-reduce:transition-none motion-reduce:hover:translate-y-0"
        @click="$emit('order')"
      >
        <span
          class="absolute inset-0 z-0 translate-x-full bg-gold-soft transition-transform
            duration-500 ease-out group-hover:translate-x-0 group-focus-visible:translate-x-0
            motion-reduce:hidden"
          aria-hidden="true"
        />
        <span class="relative z-10">{{ CONTENT.hero.cta }}</span>
        <ArrowLeft
          :size="20"
          class="relative z-10 transition-transform duration-300 ease-out
            group-hover:-translate-x-1 group-focus-visible:-translate-x-1 motion-reduce:transition-none"
        />
      </button>
    </div>
  </section>
</template>
