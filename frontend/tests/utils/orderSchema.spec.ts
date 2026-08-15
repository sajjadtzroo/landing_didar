import { describe, expect, it } from 'vitest'
import { orderSchema } from '~/utils/orderSchema'

const valid = {
  full_name: 'علی رضایی',
  phone: '09123456789',
  store_name: 'گالری طلا',
  province: 'Alborz',
}

describe('orderSchema', () => {
  it('accepts a minimal valid order and defaults contact_method to "call"', () => {
    const parsed = orderSchema.parse(valid)
    expect(parsed.contact_method).toBe('call')
    expect(parsed.full_name).toBe('علی رضایی')
  })

  it('trims full_name and rejects names shorter than 3 characters', () => {
    expect(orderSchema.parse({ ...valid, full_name: '  رضا نام  ' }).full_name).toBe('رضا نام')
    expect(orderSchema.safeParse({ ...valid, full_name: 'اب' }).success).toBe(false)
  })

  it('requires an Iranian mobile number (09 + 9 digits)', () => {
    expect(orderSchema.safeParse({ ...valid, phone: '0912345678' }).success).toBe(false)
    expect(orderSchema.safeParse({ ...valid, phone: '+989123456789' }).success).toBe(false)
    expect(orderSchema.safeParse(valid).success).toBe(true)
  })

  it('rejects provinces outside the fixed list', () => {
    expect(orderSchema.safeParse({ ...valid, province: 'Narnia' }).success).toBe(false)
  })

  it('allows note/city to be empty strings but caps note at 300 chars', () => {
    expect(orderSchema.safeParse({ ...valid, note: '', city: '' }).success).toBe(true)
    expect(orderSchema.safeParse({ ...valid, note: 'ن'.repeat(301) }).success).toBe(false)
  })
})
