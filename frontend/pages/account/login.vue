<script setup lang="ts">
import { ref } from 'vue'
import { CONTENT } from '~/constants/content'

const { requestOtp, verifyOtp } = useCustomerAuth()

const step = ref<'phone' | 'code'>('phone')
const phone = ref('')
const code = ref('')
const devCode = ref<string | null>(null)
const loading = ref(false)
const error = ref('')

const PHONE_RE = /^09\d{9}$/

async function sendCode() {
  error.value = ''
  if (!PHONE_RE.test(phone.value.trim())) {
    error.value = CONTENT.account.errBadPhone
    return
  }
  loading.value = true
  try {
    const r = await requestOtp(phone.value.trim())
    devCode.value = r.dev_code
    step.value = 'code'
  } catch {
    error.value = CONTENT.account.errGeneric
  } finally {
    loading.value = false
  }
}

async function verify() {
  error.value = ''
  loading.value = true
  try {
    await verifyOtp(phone.value.trim(), code.value.trim())
    await navigateTo('/account')
  } catch (e: unknown) {
    const s = e as { statusCode?: number; response?: { status?: number } }
    error.value = (s.statusCode === 400 || s.response?.status === 400)
      ? CONTENT.account.errBadCode
      : CONTENT.account.errGeneric
  } finally {
    loading.value = false
  }
}

useHead({ title: `${CONTENT.account.loginTitle} | ${CONTENT.brand}` })
</script>

<template>
  <main class="pt-16 sm:pt-28">
    <div class="mx-auto max-w-md px-5 pb-20 sm:px-10">
      <h1 class="text-3xl font-medium text-ink">{{ CONTENT.account.loginTitle }}</h1>

      <!-- Step 1: phone -->
      <form v-if="step === 'phone'" class="mt-6 space-y-5" novalidate @submit.prevent="sendCode">
        <p class="text-base leading-8 text-ink-muted">{{ CONTENT.account.loginSubtitle }}</p>
        <FormField :label="CONTENT.account.phone" v-slot="{ id }">
          <input
            :id="id"
            v-model="phone"
            type="tel"
            inputmode="numeric"
            dir="ltr"
            class="form-control text-start"
            autocomplete="tel"
            placeholder="09xxxxxxxxx"
          />
        </FormField>
        <button
          type="submit"
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium
            text-white transition duration-300 hover:bg-gold disabled:opacity-60"
          :disabled="loading || !phone"
        >
          {{ loading ? CONTENT.account.sending : CONTENT.account.sendCode }}
        </button>
      </form>

      <!-- Step 2: code -->
      <form v-else class="mt-6 space-y-5" novalidate @submit.prevent="verify">
        <p class="text-base leading-8 text-ink-muted">{{ CONTENT.account.codeSentTo(phone) }}</p>
        <p v-if="devCode" class="border border-line bg-surface-raised p-2 text-center text-sm text-gold-text" dir="ltr">
          {{ CONTENT.account.devCode(devCode) }}
        </p>
        <FormField :label="CONTENT.account.code" v-slot="{ id }">
          <input
            :id="id"
            v-model="code"
            type="text"
            inputmode="numeric"
            dir="ltr"
            maxlength="6"
            class="form-control text-center text-lg tracking-[0.5em]"
            autocomplete="one-time-code"
          />
        </FormField>
        <button
          type="submit"
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium
            text-white transition duration-300 hover:bg-gold disabled:opacity-60"
          :disabled="loading || code.length < 4"
        >
          {{ loading ? CONTENT.account.verifying : CONTENT.account.verify }}
        </button>
        <button type="button" class="w-full text-sm text-ink-muted hover:text-ink" @click="step = 'phone'">
          {{ CONTENT.account.changePhone }}
        </button>
      </form>

      <p v-if="error" role="alert" class="mt-5 border border-danger bg-danger-soft p-3 text-sm text-danger">
        {{ error }}
      </p>
    </div>
  </main>
</template>
