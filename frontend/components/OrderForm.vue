<script setup lang="ts">
import { toTypedSchema } from '@vee-validate/zod'
import { useField, useForm } from 'vee-validate'
import { computed, onMounted, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import { PROVINCES } from '~/constants/provinces'
import { readAttribution } from '~/plugins/attribution.client'
import { toFa } from '~/utils/format'
import { orderSchema } from '~/utils/orderSchema'

const emit = defineEmits<{ success: [{ reference: string }] }>()

const { customer, ensure } = useCustomerAuth()
// ponytail: local flag so we don't flash the wrong CTA while ensure() is in-flight
const authReady = ref(false)
const canOrder = computed(() => customer.value?.verification_status === 'approved')

const cart = useCartStore()
const {
  trackEvent,
  trackGoal,
  setCustomDimension,
  addEcommerceItem,
  trackEcommerceOrder,
} = useAnalytics()
const { public: cfg } = useRuntimeConfig()

const { handleSubmit, errors, meta } = useForm({
  validateOnMount: false,
  validationSchema: toTypedSchema(orderSchema),
})

// validateOnBlur (not on every keystroke) per the brief.
const fieldOpts = { validateOnValueUpdate: false }
const { value: full_name, handleBlur: blurName } = useField<string>('full_name', undefined, fieldOpts)
const { value: phone, handleBlur: blurPhone } = useField<string>('phone', undefined, fieldOpts)
const { value: store_name, handleBlur: blurStore } = useField<string>('store_name', undefined, fieldOpts)
const { value: province, handleBlur: blurProvince } = useField<string>('province', undefined, fieldOpts)
const { value: city } = useField<string>('city', undefined, fieldOpts)
const { value: contact_method } = useField<string>('contact_method', undefined, { ...fieldOpts, initialValue: 'call' })
const { value: note } = useField<string>('note', undefined, fieldOpts)

const honeypot = ref('') // must stay empty
const submitting = ref(false)
const serverError = ref('')
let idempotencyKey = ''
let started = false

onMounted(async () => {
  // New idempotency key each time the form mounts (double-tap can't dup).
  idempotencyKey = crypto.randomUUID()
  trackEvent('order', 'form_open', undefined, Math.round(cart.total))
  await ensure()
  authReady.value = true
})

function onFirstFocus() {
  if (started) return
  started = true
  trackEvent('order', 'form_start')
}

const submit = handleSubmit(async (values) => {
  submitting.value = true
  serverError.value = ''
  try {
    const attribution = readAttribution()
    const res = await apiFetch<{ reference: string; total: string }>('/orders', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: {
        ...values,
        website: honeypot.value,
        items: cart.items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
        ...attribution,
      },
    })
    // Custom dimensions must be set before the goal/order events fire.
    setCustomDimension(Number(cfg.matomoDimProvince), values.province)
    setCustomDimension(Number(cfg.matomoDimSource), attribution.utm_source || 'direct')
    const total = Math.round(cart.total)
    trackEvent('order', 'submitted', values.province, total)
    trackGoal(Number(cfg.matomoGoalOrder), total)
    // Ecommerce order (converts the abandoned cart into a completed order).
    for (const i of cart.items) {
      addEcommerceItem(i.sku, i.name, 'jewelry', i.price ?? 0, i.quantity)
    }
    trackEcommerceOrder(res.reference, total)
    // Push the lead into Mautic (marketing automation): map to standard fields.
    useMautic().identify({
      firstname: values.full_name,
      phone: values.phone,
      company: values.store_name,
      state: values.province,
      city: values.city,
      tags: 'didar-lead',
    })
    emit('success', { reference: res.reference })
  } catch (e: unknown) {
    const detail = (e as { data?: { detail?: string } })?.data?.detail
    serverError.value = detail || CONTENT.form.errors.generic
    // Fire form_error with the offending field if the server named one.
    const field = (e as { data?: { field?: string } })?.data?.field
    trackEvent('order', 'form_error', field || 'submit')
  } finally {
    submitting.value = false
  }
})

// Announce first client-side validation error field to analytics.
function onInvalidField(field: string) {
  if (errors.value[field as keyof typeof errors.value]) {
    trackEvent('order', 'form_error', field)
  }
}
</script>

<template>
  <form class="mx-auto max-w-xl" novalidate @submit.prevent="submit" @focusin.once="onFirstFocus">
    <!-- Cart summary -->
    <div class="mb-6 border border-line bg-surface-raised p-4">
      <p class="mb-3 text-sm text-ink-muted">{{ CONTENT.form.summary }}</p>
      <ul class="space-y-1 text-sm text-ink">
        <li v-for="i in cart.items" :key="i.productId" class="flex justify-between">
          <span>{{ i.name }} × {{ toFa(i.quantity) }}</span>
          <span class="text-gold-text">
            {{ CONTENT.products.priceOnRequest }}
          </span>
        </li>
      </ul>
    </div>

    <!-- Honeypot: visually hidden, off the tab order. Bots fill it. -->
    <div class="absolute -z-10 h-0 w-0 overflow-hidden" aria-hidden="true">
      <label>Website<input v-model="honeypot" type="text" tabindex="-1" autocomplete="off" /></label>
    </div>

    <div class="space-y-5">
      <FormField
        :label="CONTENT.form.fullName"
        :error="errors.full_name"
        required
        v-slot="{ id, describedBy }"
      >
        <input
          :id="id"
          v-model="full_name"
          type="text"
          class="form-control"
          autocomplete="name"
          :aria-describedby="describedBy"
          @blur="blurName($event); onInvalidField('full_name')"
        />
      </FormField>

      <FormField :label="CONTENT.form.phone" :error="errors.phone" required v-slot="{ id, describedBy }">
        <input
          :id="id"
          v-model="phone"
          type="tel"
          inputmode="numeric"
          class="form-control"
          autocomplete="tel"
          dir="ltr"
          :aria-describedby="describedBy"
          @blur="blurPhone($event); onInvalidField('phone')"
        />
      </FormField>

      <FormField
        :label="CONTENT.form.storeName"
        :error="errors.store_name"
        required
        v-slot="{ id, describedBy }"
      >
        <input
          :id="id"
          v-model="store_name"
          type="text"
          class="form-control"
          :aria-describedby="describedBy"
          @blur="blurStore($event); onInvalidField('store_name')"
        />
      </FormField>

      <FormField :label="CONTENT.form.province" :error="errors.province" required v-slot="{ id, describedBy }">
        <select
          :id="id"
          v-model="province"
          class="form-control"
          :aria-describedby="describedBy"
          @blur="blurProvince($event); onInvalidField('province')"
        >
          <option value="" disabled>{{ CONTENT.form.provincePlaceholder }}</option>
          <option v-for="p in PROVINCES" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
      </FormField>

      <FormField :label="CONTENT.form.city" v-slot="{ id, describedBy }">
        <input :id="id" v-model="city" type="text" class="form-control" />
      </FormField>

      <FormField :label="CONTENT.form.contactMethod" required v-slot="{ id }">
        <select :id="id" v-model="contact_method" class="form-control">
          <option value="call">{{ CONTENT.form.contactMethods.call }}</option>
          <option value="agent">{{ CONTENT.form.contactMethods.agent }}</option>
          <option value="whatsapp">{{ CONTENT.form.contactMethods.whatsapp }}</option>
        </select>
      </FormField>

      <FormField :label="CONTENT.form.note" :error="errors.note" v-slot="{ id, describedBy }">
        <textarea :id="id" v-model="note" :aria-describedby="describedBy" rows="3" maxlength="300" class="form-control h-auto py-3" />
      </FormField>
    </div>

    <p
      v-if="serverError"
      role="alert"
      class="mt-4 flex items-center justify-between gap-3 border border-danger bg-danger-soft
        p-3 text-sm text-danger"
    >
      <span>{{ serverError }}</span>
      <a :href="`tel:${CONTENT.phone}`" class="shrink-0 underline">{{ CONTENT.footer.call }}</a>
    </p>

    <!-- Auth-gated submit area: show nothing until ensure() resolves to avoid flicker -->
    <template v-if="authReady">
      <!-- Not logged in → login CTA -->
      <NuxtLink
        v-if="!customer"
        to="/account/login"
        class="mt-6 flex h-[58px] w-full items-center justify-center bg-navy text-base
          font-medium text-white transition duration-300 hover:bg-gold"
      >
        برای ثبت سفارش وارد شوید
      </NuxtLink>

      <!-- Logged in but not approved → disabled button + verification notice -->
      <template v-else-if="!canOrder">
        <button
          type="button"
          disabled
          class="mt-6 flex h-[58px] w-full items-center justify-center bg-navy text-base
            font-medium text-white opacity-60"
        >
          {{ CONTENT.form.submit }}
        </button>
        <p class="mt-3 text-sm text-ink-muted text-center">
          برای ثبت سفارش ابتدا
          <NuxtLink to="/account/verification" class="text-navy underline underline-offset-2">
            احراز هویت خود را کامل کنید
          </NuxtLink>
        </p>
      </template>

      <!-- Approved → normal submit -->
      <button
        v-else
        type="submit"
        class="mt-6 flex h-[58px] w-full items-center justify-center bg-navy text-base
          font-medium text-white transition duration-300 hover:bg-gold disabled:opacity-60"
        :disabled="submitting || !cart.items.length"
      >
        {{ submitting ? CONTENT.form.submitting : CONTENT.form.submit }}
      </button>
    </template>

    <!-- While auth is resolving: disabled placeholder to avoid layout jump -->
    <button
      v-else
      type="button"
      disabled
      class="mt-6 flex h-[58px] w-full items-center justify-center bg-navy text-base
        font-medium text-white opacity-60"
    >
      {{ CONTENT.form.submit }}
    </button>

    <p v-if="meta.dirty && !meta.valid" class="sr-only" aria-live="polite">فرم دارای خطاست.</p>
  </form>
</template>
