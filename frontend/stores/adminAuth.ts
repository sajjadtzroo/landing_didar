import { defineStore } from 'pinia'

export const useAdminAuth = defineStore('adminAuth', {
  state: () => ({ username: '' as string, role: '' as string, unread: 0 }),
  getters: {
    isSuperadmin: (s) => s.role === 'superadmin',
  },
  actions: {
    async login(username: string, password: string) {
      const res = await apiFetch<{ username: string; role: string }>('/admin/login', {
        method: 'POST',
        body: { username, password },
      })
      this.username = res.username
      this.role = res.role
    },
    setIdentity(username: string, role: string) {
      this.username = username
      this.role = role
    },
    async logout() {
      await apiFetch('/admin/logout', { method: 'POST' })
      this.username = ''
      this.role = ''
      await navigateTo('/admin/login')
    },
    setUnread(n: number) {
      this.unread = n
    },
  },
})
