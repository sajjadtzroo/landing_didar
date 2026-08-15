<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import { onMounted, reactive, ref } from 'vue'
import { CONTENT } from '~/constants/content'
import { PROVINCES } from '~/constants/provinces'
import type { CustomerAddress } from '~/types'

definePageMeta({ middleware: 'customer' })

const { customer, ensure } = useCustomerAuth()

const fullName = ref('')
const savingName = ref(false)
const nameSaved = ref(false)

const addresses = ref<CustomerAddress[]>([])
const form = reactive({ title: '', province: '', city: '', line: '', is_default: false })
const adding = ref(false)

onMounted(async () => {
  await ensure()
  fullName.value = customer.value?.full_name || ''
  addresses.value = await apiFetch<CustomerAddress[]>('/account/me/addresses').catch(() => [])
})

async function saveName() {
  savingName.value = true
  nameSaved.value = false
  try {
    await apiFetch('/account/me', { method: 'PATCH', body: { full_name: fullName.value } })
    if (customer.value) customer.value.full_name = fullName.value
    nameSaved.value = true
  } finally {
    savingName.value = false
  }
}

async function addAddress() {
  if (!form.title || !form.province || form.line.length < 3) return
  adding.value = true
  try {
    const created = await apiFetch<CustomerAddress>('/account/me/addresses', {
      method: 'POST',
      body: { ...form, city: form.city || null },
    })
    // A new default demotes the others locally too.
    if (created.is_default) addresses.value.forEach((a) => (a.is_default = false))
    addresses.value.push(created)
    Object.assign(form, { title: '', province: '', city: '', line: '', is_default: false })
  } finally {
    adding.value = false
  }
}

async function removeAddress(id: string) {
  await apiFetch(`/account/me/addresses/${id}`, { method: 'DELETE' })
  addresses.value = addresses.value.filter((a) => a.id !== id)
}

useHead({ title: `${CONTENT.account.profileTitle} | ${CONTENT.brand}` })
</script>

<template>
  <AccountShell>
    <h2 class="mb-6 text-xl text-ink">{{ CONTENT.account.profileTitle }}</h2>

    <!-- Name -->
    <form class="max-w-md space-y-4" @submit.prevent="saveName">
      <FormField :label="CONTENT.account.fullName" v-slot="{ id }">
        <input :id="id" v-model="fullName" type="text" class="form-control" autocomplete="name" />
      </FormField>
      <div class="flex items-center gap-3">
        <button
          type="submit"
          class="flex h-11 items-center bg-navy px-5 text-sm text-white hover:bg-gold disabled:opacity-60"
          :disabled="savingName"
        >
          {{ CONTENT.account.save }}
        </button>
        <span v-if="nameSaved" class="text-sm text-success">{{ CONTENT.account.saved }}</span>
      </div>
    </form>

    <!-- Addresses -->
    <h3 class="mb-4 mt-10 text-lg text-ink">{{ CONTENT.account.addressesTitle }}</h3>

    <ul v-if="addresses.length" class="mb-6 space-y-3">
      <li v-for="a in addresses" :key="a.id" class="flex items-start justify-between border border-line bg-surface-raised p-4">
        <div>
          <p class="flex items-center gap-2 text-ink">
            {{ a.title }}
            <span v-if="a.is_default" class="bg-gold px-2 py-0.5 text-[11px] font-medium text-navy-deep">
              {{ CONTENT.account.defaultBadge }}
            </span>
          </p>
          <p class="mt-1 text-sm text-ink-muted">{{ a.province }}{{ a.city ? '، ' + a.city : '' }} — {{ a.line }}</p>
        </div>
        <button
          type="button"
          class="text-ink-muted hover:text-danger"
          :aria-label="CONTENT.account.remove"
          @click="removeAddress(a.id)"
        >
          <Trash2 :size="16" />
        </button>
      </li>
    </ul>
    <p v-else class="mb-6 text-sm text-ink-muted">{{ CONTENT.account.addressesEmpty }}</p>

    <!-- Add address -->
    <form class="max-w-md space-y-4 border-t border-line pt-6" @submit.prevent="addAddress">
      <FormField :label="CONTENT.account.addrTitle" required v-slot="{ id }">
        <input :id="id" v-model="form.title" type="text" class="form-control" />
      </FormField>
      <FormField :label="CONTENT.account.addrProvince" required v-slot="{ id }">
        <select :id="id" v-model="form.province" autocomplete="address-level1" class="form-control">
          <option value="" disabled>{{ CONTENT.form.provincePlaceholder }}</option>
          <option v-for="p in PROVINCES" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
      </FormField>
      <FormField :label="CONTENT.account.addrCity" v-slot="{ id }">
        <input :id="id" v-model="form.city" type="text" autocomplete="address-level2" class="form-control" />
      </FormField>
      <FormField :label="CONTENT.account.addrLine" required v-slot="{ id }">
        <textarea :id="id" v-model="form.line" rows="2" maxlength="300" class="form-control h-auto py-3" />
      </FormField>
      <label class="flex items-center gap-2 text-sm text-ink">
        <input v-model="form.is_default" type="checkbox" /> {{ CONTENT.account.addrDefault }}
      </label>
      <button
        type="submit"
        class="flex h-11 items-center bg-navy px-5 text-sm text-white hover:bg-gold disabled:opacity-60"
        :disabled="adding"
      >
        {{ CONTENT.account.addAddress }}
      </button>
    </form>
  </AccountShell>
</template>
