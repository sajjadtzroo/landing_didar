// Gate the customer panel. /account/** is client-rendered (ssr:false), so this
// runs in the browser where the session cookie is available.
export default defineNuxtRouteMiddleware(async () => {
  if (import.meta.server) return
  const { ensure } = useCustomerAuth()
  if (!(await ensure())) {
    return navigateTo('/account/login')
  }
})
