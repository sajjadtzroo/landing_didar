<script setup lang="ts">
import { Minus, Plus } from 'lucide-vue-next'
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'
import type { FAQ } from '~/types'

defineProps<{ faqs: FAQ[] }>()

const { trackEvent } = useAnalytics()
const open = ref(0) // first item open by default

function toggle(i: number, question: string) {
  const wasOpen = open.value === i
  open.value = wasOpen ? -1 : i
  if (!wasOpen) trackEvent('faq', 'open', question)
}
</script>

<template>
  <section id="faq" class="bg-surface-soft py-16">
    <div class="mx-auto max-w-3xl px-5 sm:px-10">
      <SectionDivider
        :eyebrow="CONTENT.faq.eyebrow"
        :title="CONTENT.faq.title"
        :description="CONTENT.faq.description"
      />

      <!-- Each FAQ is an elevated card; the open one lifts with a gold ring. -->
      <div class="space-y-3">
        <div
          v-for="(faq, i) in faqs"
          :key="faq.id"
          class="corner-soft border bg-surface-raised transition-all duration-300"
          :class="
            open === i
              ? 'border-gold shadow-luxury'
              : 'border-line hover:border-gold-soft'
          "
        >
          <h3>
            <button
              :id="`faq-btn-${i}`"
              type="button"
              class="flex min-h-[60px] w-full items-center justify-between gap-4 px-5 py-4
                text-start sm:px-6"
              :aria-expanded="open === i"
              :aria-controls="`faq-panel-${i}`"
              @click="toggle(i, faq.question)"
            >
              <span class="text-base font-medium text-ink sm:text-lg">
                {{ faq.question }}
              </span>
              <!-- Diamond +/− chip: rotated square border (matches the brand ✦
                   motif); fills gold when open. Icon is counter-rotated upright. -->
              <span
                class="flex h-8 w-8 shrink-0 rotate-45 items-center justify-center border
                  transition-colors duration-300"
                :class="
                  open === i
                    ? 'border-gold bg-gold text-white'
                    : 'border-gold-soft text-gold-text'
                "
                aria-hidden="true"
              >
                <Minus v-if="open === i" :size="15" :stroke-width="2.5" class="-rotate-45" />
                <Plus v-else :size="15" :stroke-width="2.5" class="-rotate-45" />
              </span>
            </button>
          </h3>

          <!-- Smooth height reveal via grid-rows (0fr → 1fr); clamps under
               prefers-reduced-motion. Panel stays in the DOM for a11y. -->
          <div
            :id="`faq-panel-${i}`"
            role="region"
            :aria-labelledby="`faq-btn-${i}`"
            class="grid transition-[grid-template-rows] duration-300 ease-out"
            :class="open === i ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
          >
            <div class="overflow-hidden">
              <p class="px-5 pb-6 text-sm leading-8 text-ink-muted sm:px-6">
                {{ faq.answer }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
