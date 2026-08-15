import { describe, expect, it } from 'vitest'
import {
  formatGrams,
  formatGramsCompact,
  formatPrice,
  formatTomanCompact,
  toFa,
} from '~/utils/format'

describe('toFa', () => {
  it('converts Latin digits to Persian, leaving other characters alone', () => {
    expect(toFa('123')).toBe('۱۲۳')
    expect(toFa(405)).toBe('۴۰۵')
    expect(toFa('ab-1.2')).toBe('ab-۱.۲')
  })
})

describe('formatPrice', () => {
  it('groups thousands and appends تومان in Persian digits', () => {
    expect(formatPrice(1500000)).toBe('۱,۵۰۰,۰۰۰ تومان')
    expect(formatPrice('2500')).toBe('۲,۵۰۰ تومان')
  })

  it('returns null for null or non-numeric input', () => {
    expect(formatPrice(null)).toBeNull()
    expect(formatPrice('abc')).toBeNull()
  })
})

describe('formatGrams', () => {
  it('formats weight with up to 2 decimals and گرم suffix', () => {
    expect(formatGrams('12.5')).toBe('۱۲.۵ گرم')
    expect(formatGrams(1234.567)).toBe('۱,۲۳۴.۵۷ گرم')
    expect(formatGrams(null)).toBeNull()
  })
})

describe('formatGramsCompact', () => {
  it('rolls grams up through kg and tonne', () => {
    expect(formatGramsCompact(553)).toBe('۵۵۳ گرم')
    expect(formatGramsCompact(1200)).toBe('۱.۲ کیلوگرم')
    expect(formatGramsCompact(363_000_000)).toBe('۳۶۳ تن')
  })

  it('falls back to an em dash for missing values', () => {
    expect(formatGramsCompact(null)).toBe('—')
    expect(formatGramsCompact('abc')).toBe('—')
  })
})

describe('formatTomanCompact', () => {
  it('rolls Toman up through میلیون and میلیارد', () => {
    expect(formatTomanCompact(900)).toBe('۹۰۰ تومان')
    expect(formatTomanCompact(553_000_000)).toBe('۵۵۳ میلیون تومان')
    expect(formatTomanCompact(1_200_000_000)).toBe('۱.۲ میلیارد تومان')
    expect(formatTomanCompact(null)).toBe('—')
  })
})
