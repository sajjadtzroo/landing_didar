import { defineStore } from 'pinia'

export const useAdminAuth = defineStore('adminAuth', {
  state: () => ({ username: '' as string, unread: 0 }),
  actions: {
    async login(username: string, password: string) {
      const res = await apiFetch<{ username: string }>('/admin/login', {
        method: 'POST',
        body: { username, password },
      })
      this.username = res.username
    },
    async logout() {
      await apiFetch('/admin/logout', { method: 'POST' })
      this.username = ''
      await navigateTo('/admin/login')
    },
    setUnread(n: number) {
      this.unread = n
    },
  },
})
