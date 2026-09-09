<script setup lang="ts">
import { ref } from 'vue'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const { data: settings, refresh } = await useAsyncData('admin-settings', () =>
  apiFetch<{ price_requires_login: boolean }>('/admin/settings'),
)

const saving = ref(false)
const saved = ref(false)
const error = ref('')

async function toggle() {
  if (!settings.value) return
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    await apiFetch('/admin/settings', {
      method: 'PATCH',
      body: { price_requires_login: !settings.value.price_requires_login },
    })
    await refresh()
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } catch {
    error.value = 'خطا در ذخیره‌سازی — دوباره تلاش کنید'
    await refresh()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-8 p-6">
    <h1 class="text-2xl font-bold text-ink">تنظیمات سایت</h1>

    <div class="rounded-lg border border-line bg-surface-raised p-6">
      <h2 class="mb-1 text-lg font-semibold text-ink">نمایش مشخصات محصولات</h2>
      <p class="mb-5 text-sm text-ink-muted">
        وزن، عیار و اجرت محصولات برای چه کسانی نمایش داده شود؟
      </p>

      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="font-medium text-ink">
            {{ settings?.price_requires_login ? 'فقط برای کاربران وارد‌شده' : 'برای همه بازدیدکنندگان' }}
          </p>
          <p class="mt-0.5 text-sm text-ink-muted">
            {{ settings?.price_requires_login
              ? 'کاربران مهمان پیام «برای مشاهده وارد شوید» را می‌بینند.'
              : 'مشخصات محصول بدون ورود هم قابل مشاهده است.' }}
          </p>
        </div>

        <!-- Toggle switch -->
        <button
          type="button"
          role="switch"
          :aria-checked="settings?.price_requires_login"
          class="relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2
            border-transparent transition-colors duration-200 focus:outline-none
            focus:ring-2 focus:ring-gold focus:ring-offset-2"
          :class="settings?.price_requires_login ? 'bg-navy' : 'bg-line'"
          :disabled="saving"
          @click="toggle"
        >
          <span
            class="pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white
              shadow ring-0 transition duration-200"
            :class="settings?.price_requires_login ? 'translate-x-5' : 'translate-x-0'"
          />
        </button>
      </div>

      <p v-if="saved" class="mt-4 text-sm text-green-600">✓ ذخیره شد</p>
      <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
    </div>
  </div>
</template>
