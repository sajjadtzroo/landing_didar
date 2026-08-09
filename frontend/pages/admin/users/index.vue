<script setup lang="ts">
import { Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import type { AdminRole, PanelUser } from '~/types'
import { toFa } from '~/utils/format'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const ROLE_LABEL: Record<AdminRole, string> = {
  superadmin: 'مدیر ارشد',
  operator: 'اپراتور',
  retailer: 'خرده‌فروش',
  agent: 'ایجنت',
  support: 'پشتیبانی',
}
const ROLE_CLASS: Record<AdminRole, string> = {
  superadmin: 'bg-warning-soft text-warning',
  operator: 'bg-success-soft text-success',
  retailer: 'bg-surface-soft text-ink-muted',
  agent: 'bg-surface-soft text-ink-muted',
  support: 'bg-surface-soft text-ink-muted',
}

const auth = useAdminAuth()
const { data: users, refresh } = await useAsyncData('admin-users', () =>
  apiFetch<PanelUser[]>('/admin/users'),
)

const blank = () => ({
  id: '',
  username: '',
  password: '',
  full_name: '',
  phone: '',
  role: 'operator' as AdminRole,
  is_active: true,
})
const form = reactive(blank())
const editing = ref(false)
const panelOpen = ref(false)
const error = ref('')

function startCreate() {
  Object.assign(form, blank())
  editing.value = false
  error.value = ''
  panelOpen.value = true
}
function startEdit(u: PanelUser) {
  Object.assign(form, {
    id: u.id,
    username: u.username,
    password: '',
    full_name: u.full_name ?? '',
    phone: u.phone ?? '',
    role: u.role,
    is_active: u.is_active,
  })
  editing.value = true
  error.value = ''
  panelOpen.value = true
}

async function save() {
  error.value = ''
  try {
    if (editing.value) {
      await apiFetch(`/admin/users/${form.id}`, {
        method: 'PATCH',
        body: {
          full_name: form.full_name || null,
          phone: form.phone || null,
          role: form.role,
          is_active: form.is_active,
          ...(form.password ? { password: form.password } : {}),
        },
      })
    } else {
      await apiFetch('/admin/users', {
        method: 'POST',
        body: {
          username: form.username,
          password: form.password,
          full_name: form.full_name || null,
          phone: form.phone || null,
          role: form.role,
        },
      })
    }
    panelOpen.value = false
    await refresh()
  } catch (e: any) {
    error.value = e?.data?.detail || 'ذخیره ناموفق بود.'
  }
}

async function remove(u: PanelUser) {
  if (!confirm(`حذف کاربر «${u.username}»؟`)) return
  await apiFetch(`/admin/users/${u.id}`, { method: 'DELETE' })
  await refresh()
}

function faDate(iso: string) {
  return toFa(new Date(iso).toLocaleDateString('en-GB'))
}
</script>

<template>
  <div>
    <AdminPageHeader title="کاربران" subtitle="دسترسی نقش‌محور؛ خرده‌فروش و ایجنت در فاز بعد فعال می‌شوند.">
      <button
        class="flex h-11 items-center gap-2 bg-navy px-4 text-sm text-white hover:bg-gold"
        @click="startCreate"
      >
        <Plus :size="16" /> کاربر جدید
      </button>
    </AdminPageHeader>

    <div class="admin-card hidden overflow-x-auto p-0 md:block">
      <table class="w-full text-start text-sm">
        <thead class="bg-surface-soft text-ink-muted">
          <tr>
            <th class="p-3 text-start">نام کاربری</th>
            <th class="p-3 text-start">نام</th>
            <th class="p-3 text-start">نقش</th>
            <th class="p-3 text-start">وضعیت</th>
            <th class="p-3 text-start">ایجاد</th>
            <th class="p-3 text-start"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-t border-line hover:bg-surface-soft">
            <td class="tnum p-3 font-medium" dir="ltr">{{ u.username }}</td>
            <td class="p-3">{{ u.full_name ?? '—' }}</td>
            <td class="p-3">
              <span class="px-2 py-1 text-xs" :class="ROLE_CLASS[u.role]">{{ ROLE_LABEL[u.role] }}</span>
            </td>
            <td class="p-3">
              <span class="px-2 py-1 text-xs" :class="u.is_active ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'">
                {{ u.is_active ? 'فعال' : 'غیرفعال' }}
              </span>
            </td>
            <td class="tnum p-3 text-ink-muted">{{ faDate(u.created_at) }}</td>
            <td class="p-3 text-end">
              <button class="me-2 text-ink-muted hover:text-gold-text" aria-label="ویرایش" @click="startEdit(u)">
                <Pencil :size="16" />
              </button>
              <button
                v-if="u.username !== auth.username"
                class="text-ink-muted hover:text-danger"
                aria-label="حذف"
                @click="remove(u)"
              >
                <Trash2 :size="16" />
              </button>
            </td>
          </tr>
          <tr v-if="!users?.length">
            <td colspan="6" class="p-10 text-center text-ink-muted">
              کاربری تعریف نشده — ورود فعلی شما از تنظیمات سیستم (مدیر ارشد) است.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile cards -->
    <div class="space-y-3 md:hidden">
      <div v-for="u in users" :key="u.id" class="admin-card p-4">
        <div class="flex items-center justify-between gap-2">
          <span class="tnum font-medium" dir="ltr">{{ u.username }}</span>
          <span class="px-2 py-1 text-xs" :class="ROLE_CLASS[u.role]">{{ ROLE_LABEL[u.role] }}</span>
        </div>
        <div class="mt-2 flex items-center justify-between text-sm">
          <span>{{ u.full_name ?? '—' }}</span>
          <button class="text-ink-muted hover:text-gold-text" aria-label="ویرایش" @click="startEdit(u)">
            <Pencil :size="16" />
          </button>
        </div>
      </div>
      <p v-if="!users?.length" class="admin-card p-6 text-center text-sm text-ink-muted">
        کاربری تعریف نشده است.
      </p>
    </div>

    <BaseSheet v-model="panelOpen" :title="editing ? 'ویرایش کاربر' : 'کاربر جدید'">
      <div class="space-y-4">
        <FormField label="نام کاربری" v-slot="{ id }">
          <input :id="id" v-model="form.username" dir="ltr" class="form-control" :disabled="editing" :class="editing ? 'opacity-60' : ''" />
        </FormField>
        <FormField :label="editing ? 'گذرواژه جدید (خالی = بدون تغییر)' : 'گذرواژه (حداقل ۸ کاراکتر)'" v-slot="{ id }">
          <input :id="id" v-model="form.password" type="password" dir="ltr" class="form-control" />
        </FormField>
        <FormField label="نام و نام خانوادگی (اختیاری)" v-slot="{ id }">
          <input :id="id" v-model="form.full_name" class="form-control" />
        </FormField>
        <FormField label="موبایل (اختیاری)" v-slot="{ id }">
          <input :id="id" v-model="form.phone" dir="ltr" class="form-control" />
        </FormField>
        <FormField label="نقش" v-slot="{ id }">
          <select :id="id" v-model="form.role" class="form-control" :disabled="editing && form.username === auth.username">
            <option value="superadmin">مدیر ارشد</option>
            <option value="operator">اپراتور</option>
            <option value="retailer">خرده‌فروش (فاز بعد)</option>
            <option value="agent">ایجنت (فاز بعد)</option>
            <option value="support">پشتیبانی</option>
          </select>
        </FormField>
        <label v-if="editing" class="flex items-center gap-2 text-sm">
          <input v-model="form.is_active" type="checkbox" :disabled="form.username === auth.username" /> فعال
        </label>
        <p v-if="error" class="text-sm text-danger">{{ error }}</p>
      </div>
      <template #footer>
        <button
          class="flex h-[58px] w-full items-center justify-center bg-navy text-base font-medium text-white hover:bg-gold disabled:opacity-60"
          :disabled="!form.username || (!editing && form.password.length < 8)"
          @click="save"
        >
          ذخیره
        </button>
      </template>
    </BaseSheet>
  </div>
</template>
