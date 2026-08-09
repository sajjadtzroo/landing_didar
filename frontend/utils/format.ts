const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']

/** Latin digits → Persian, for display only. */
export function toFa(input: string | number): string {
  return String(input).replace(/\d/g, (d) => FA_DIGITS[Number(d)])
}

/** Group a Toman amount with separators and Persian digits. */
export function formatPrice(value: number | string | null): string | null {
  if (value == null) return null
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return null
  return toFa(n.toLocaleString('en-US')) + ' تومان'
}

/** Weight in grams with Persian digits: "۱۲٫۵ گرم" (wholesale gold is by weight). */
export function formatGrams(value: number | string | null): string | null {
  if (value == null) return null
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return null
  return toFa(n.toLocaleString('en-US', { maximumFractionDigits: 2 })) + ' گرم'
}

/** Compact grams for KPI cards: "۵۵۳ گرم" / "۱٫۲ کیلوگرم" / "۳۶۳ تن".
 *  Rolls up through kg→tonne and groups thousands so big totals stay one line. */
export function formatGramsCompact(value: number | string | null): string {
  const n = typeof value === 'string' ? Number(value) : value
  if (n == null || Number.isNaN(n)) return '—'
  const fmt = (x: number) => toFa(x.toLocaleString('en-US', { maximumFractionDigits: 1 }))
  if (n >= 1_000_000) return `${fmt(n / 1_000_000)} تن`
  if (n >= 1000) return `${fmt(n / 1000)} کیلوگرم`
  return `${fmt(n)} گرم`
}

/** Compact Toman for KPI cards: ۵۵۳ میلیون / ۱٫۲ میلیارد تومان (single line). */
export function formatTomanCompact(value: number | string | null): string {
  const n = typeof value === 'string' ? Number(value) : value
  if (n == null || Number.isNaN(n)) return '—'
  if (n >= 1_000_000_000) return `${toFa((n / 1_000_000_000).toFixed(1))} میلیارد تومان`
  if (n >= 1_000_000) return `${toFa(Math.round(n / 1_000_000))} میلیون تومان`
  return `${toFa(n.toLocaleString('en-US'))} تومان`
}
