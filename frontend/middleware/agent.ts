// Agent-portal guard: session must belong to an agent (superadmin allowed for
// oversight). Panel roles are sent back to the admin panel.
export default defineNuxtRouteMiddleware(async () => {
  try {
    const me = await apiFetch<{ username: string; role: string }>('/admin/me')
    useAdminAuth().setIdentity(me.username, me.role)
    if (me.role !== 'agent' && me.role !== 'superadmin') return navigateTo('/admin')
  } catch {
    return navigateTo('/admin/login')
  }
})
