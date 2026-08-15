/**
 * Customer session (phone-OTP). Cookie-based, so state is just a cache of /me.
 * SSR-safe via useState; /account/** is client-rendered so calls run in-browser.
 */
import type { Customer } from '~/types'

export function useCustomerAuth() {
  const customer = useState<Customer | null>('customer', () => null)
  const loaded = useState<boolean>('customer-loaded', () => false)

  async function requestOtp(phone: string) {
    return apiFetch<{ sent: boolean; dev_code: string | null }>(
      '/account/otp/request',
      { method: 'POST', body: { phone } },
    )
  }

  async function verifyOtp(phone: string, code: string) {
    const c = await apiFetch<Customer>('/account/otp/verify', {
      method: 'POST',
      body: { phone, code },
    })
    customer.value = c
    loaded.value = true
    // Matomo userId: joins this customer's sessions across devices/visits.
    useAnalytics().setUserId(c.phone)
    // Merge the guest wishlist into the account (upload local + pull server).
    await useFavorites().syncOnLogin()
    return c
  }

  // Load /me once; returns the customer or null (401). Cached after first call.
  async function ensure(force = false): Promise<Customer | null> {
    if (loaded.value && !force) return customer.value
    try {
      customer.value = await apiFetch<Customer>('/account/me')
      if (customer.value) useAnalytics().setUserId(customer.value.phone)
    } catch {
      customer.value = null
    }
    loaded.value = true
    return customer.value
  }

  async function logout() {
    await apiFetch('/account/logout', { method: 'POST' }).catch(() => {})
    customer.value = null
    loaded.value = true
    useAnalytics().resetUserId()
  }

  return { customer, requestOtp, verifyOtp, ensure, logout }
}
