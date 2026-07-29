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
