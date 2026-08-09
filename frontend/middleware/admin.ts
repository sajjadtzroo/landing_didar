// Client-only guard (the whole /admin tree is ssr:false). Verifies the session
// against GET /admin/me and bounces to login on 401. Hydrates the identity
// (username + role) so the sidebar can gate superadmin sections.
export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/admin/login') return
  try {
    const me = await apiFetch<{ username: string; role: string }>('/admin/me')
    useAdminAuth().setIdentity(me.username, me.role)
    if (me.role === 'agent') return navigateTo('/agent')
  } catch {
    return navigateTo('/admin/login')
  }
})
