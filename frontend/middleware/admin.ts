// Client-only guard (the whole /admin tree is ssr:false). Verifies the session
// against GET /admin/me and bounces to login on 401.
export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/admin/login') return
  try {
    await apiFetch('/admin/me')
  } catch {
    return navigateTo('/admin/login')
  }
})
