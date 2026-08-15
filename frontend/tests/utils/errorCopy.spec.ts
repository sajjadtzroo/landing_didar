import { describe, expect, it } from 'vitest'
import { errorCopy } from '~/utils/errorCopy'

describe('errorCopy', () => {
  it('maps the statuses users actually hit', () => {
    expect(errorCopy(404).title).toBe('صفحه پیدا نشد')
    expect(errorCopy(401).title).toBe('ورود لازم است')
    expect(errorCopy(403).title).toBe('دسترسی مجاز نیست')
    expect(errorCopy(429).retry).toBe(true)
  })

  it('buckets unknown 5xx as retryable server errors', () => {
    for (const code of [500, 501, 502, 503, 504, 599]) {
      const c = errorCopy(code)
      expect(c.retry).toBe(true)
      expect(c.title.length).toBeGreaterThan(0)
    }
  })

  it('buckets unknown 4xx as non-retryable with generic copy', () => {
    const c = errorCopy(418)
    expect(c.retry).toBe(false)
    expect(c.title).toBe('امکان پردازش درخواست نیست')
  })

  it('treats a missing status as 500', () => {
    expect(errorCopy(undefined).retry).toBe(true)
  })

  it('every entry has Persian, non-empty copy', () => {
    for (const code of [400, 401, 403, 404, 408, 410, 422, 429, 500, 502, 503, 504]) {
      const c = errorCopy(code)
      expect(c.title).toMatch(/[؀-ۿ]/)
      expect(c.message).toMatch(/[؀-ۿ]/)
    }
  })
})
