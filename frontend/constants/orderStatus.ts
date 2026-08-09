import type { OrderStatus } from '~/types'

export const STATUS_FLOW: OrderStatus[] = [
  'new',
  'contacted',
  'confirmed',
  'preparing',
  'shipped',
  'delivered',
  'cancelled',
]

export const STATUS_LABEL: Record<OrderStatus, string> = {
  new: 'جدید',
  contacted: 'تماس گرفته‌شده',
  confirmed: 'تأییدشده',
  preparing: 'در حال آماده‌سازی',
  shipped: 'ارسال‌شده',
  delivered: 'تحویل‌شده',
  cancelled: 'لغوشده',
}

// Muted background + full-strength text (design system badge rule).
export const STATUS_CLASS: Record<OrderStatus, string> = {
  new: 'bg-warning-soft text-warning',
  contacted: 'bg-surface-soft text-ink-muted',
  confirmed: 'bg-success-soft text-success',
  preparing: 'bg-warning-soft text-warning',
  shipped: 'bg-success-soft text-success',
  delivered: 'bg-success-soft text-success',
  cancelled: 'bg-danger-soft text-danger',
}
