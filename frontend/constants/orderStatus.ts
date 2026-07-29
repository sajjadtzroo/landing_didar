import type { OrderStatus } from '~/types'

export const STATUS_FLOW: OrderStatus[] = [
  'new',
  'contacted',
  'confirmed',
  'shipped',
  'cancelled',
]

export const STATUS_LABEL: Record<OrderStatus, string> = {
  new: 'جدید',
  contacted: 'تماس گرفته‌شده',
  confirmed: 'تأییدشده',
  shipped: 'ارسال‌شده',
  cancelled: 'لغوشده',
}

// Muted background + full-strength text (design system badge rule).
export const STATUS_CLASS: Record<OrderStatus, string> = {
  new: 'bg-warning-soft text-warning',
  contacted: 'bg-surface-soft text-ink-muted',
  confirmed: 'bg-success-soft text-success',
  shipped: 'bg-success-soft text-success',
  cancelled: 'bg-danger-soft text-danger',
}
