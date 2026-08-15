<script setup lang="ts">
import { ref } from 'vue'

definePageMeta({ layout: false })

const auth = useAdminAuth()
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    // Field agents land in their own portal; panel roles go to orders.
    await navigateTo(auth.role === 'agent' ? '/agent' : '/admin/orders')
  } catch {
    error.value = 'نام کاربری یا رمز عبور نادرست است.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-navy px-6" data-theme="dark">
    <!-- Always-navy login screen (matches the brand's login treatment). -->
    <form
      class="w-full max-w-sm border border-gold/30 bg-navy-deep p-8"
      @submit.prevent="submit"
    >
      <BrandLogo :height="34" class="mx-auto mb-6 block" />
      <p class="mb-8 text-center text-lg font-medium text-cream">پنل مدیریت دیدار گلد</p>
      <div class="space-y-4">
        <input
          v-model="username"
          type="text"
          placeholder="نام کاربری"
          class="h-14 w-full border border-gold/40 bg-navy px-4 text-sm text-cream
            placeholder:text-cream/50 focus:border-gold"
          autocomplete="username"
        />
        <input
          v-model="password"
          type="password"
          placeholder="رمز عبور"
          class="h-14 w-full border border-gold/40 bg-navy px-4 text-sm text-cream
            placeholder:text-cream/50 focus:border-gold"
          autocomplete="current-password"
        />
      </div>
      <p v-if="error" role="alert" class="mt-3 text-sm text-danger-bright">{{ error }}</p>
      <button
        type="submit"
        class="mt-6 flex h-[58px] w-full items-center justify-center bg-gold text-base
          font-medium text-white transition duration-300 hover:bg-cream hover:text-navy
          disabled:opacity-60"
        :disabled="busy"
      >
        {{ busy ? 'در حال ورود…' : 'ورود' }}
      </button>
    </form>
  </div>
</template>
