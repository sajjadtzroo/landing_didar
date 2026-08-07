import type { Customer } from '~/types'

// Uploads a verification document; returns the updated customer.
export function useCustomerUpload() {
  async function upload(file: File): Promise<Customer> {
    const form = new FormData()
    form.append('file', file)
    return apiFetch<Customer>('/account/me/documents', {
      method: 'POST',
      body: form,
    })
  }
  async function remove(idx: number): Promise<Customer> {
    return apiFetch<Customer>(`/account/me/documents/${idx}`, {
      method: 'DELETE',
    })
  }
  return { upload, remove }
}
