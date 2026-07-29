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

/** Compact Toman for KPI cards: ۵۵۳ میلیون / ۱٫۲ میلیارد تومان (single line). */
export function formatTomanCompact(value: number | string | null): string {
  const n = typeof value === 'string' ? Number(value) : value
  if (n == null || Number.isNaN(n)) return '—'
  if (n >= 1_000_000_000) return `${toFa((n / 1_000_000_000).toFixed(1))} میلیارد تومان`
  if (n >= 1_000_000) return `${toFa(Math.round(n / 1_000_000))} میلیون تومان`
  return `${toFa(n.toLocaleString('en-US'))} تومان`
}
