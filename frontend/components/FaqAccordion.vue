<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
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
      <div class="divide-y divide-line border-y border-line">
        <div
          v-for="(faq, i) in faqs"
          :key="faq.id"
          class="border-s-2 transition-colors duration-300"
          :class="open === i ? 'border-gold ps-4' : 'border-transparent'"
        >
          <h3>
            <button
              :id="`faq-btn-${i}`"
              type="button"
              class="flex w-full items-center justify-between gap-4 py-5 text-start
                text-ink"
              :aria-expanded="open === i"
              :aria-controls="`faq-panel-${i}`"
              @click="toggle(i, faq.question)"
            >
              <span class="text-lg">{{ faq.question }}</span>
              <ChevronDown
                :size="20"
                class="shrink-0 text-gold-text transition-transform duration-300"
                :class="open === i ? 'rotate-180' : ''"
              />
            </button>
          </h3>
          <div
            v-show="open === i"
            :id="`faq-panel-${i}`"
            role="region"
            :aria-labelledby="`faq-btn-${i}`"
            class="pb-6 text-sm leading-8 text-ink-muted"
          >
            {{ faq.answer }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
