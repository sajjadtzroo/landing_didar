export interface Product {
  id: string
  name: string
  slug: string
  sku: string
  description: string | null
  weight_grams: string | null
  karat: number | null
  price: string | null // null => price on request
  ojrat_percent: string | null // اجرت (making-fee %)
  image_url: string | null
  category: 'daily' | 'lux_daily' | 'luxury' // landing carousel grouping
  is_active: boolean
  sort_order: number
}

export interface FAQ {
  id: string
  question: string
  answer: string
  is_active: boolean
  sort_order: number
}

// Public landing payload (GET /landings/{slug}).
export interface Landing {
  slug: string
  title: string
  hero_video_url: string | null
  hero_poster_url: string | null
  content: Record<string, any>
  groups: LandingGroup[]
}

// One product carousel on a landing (backend resolves product_ids → products).
export interface LandingGroup {
  title: string
  eyebrow: string | null
  description: string | null
  products: Product[]
}

// Admin landing payload (GET /admin/landings) — raw content (groups hold ids).
export interface AdminLanding {
  id: string
  slug: string
  title: string
  hero_video_url: string | null
  hero_poster_url: string | null
  content: Record<string, any> | null
}

// Public portfolio (GET /portfolios) — a curated /shop section; backend resolves
// each group's product_ids → products. Reuses the landing group shape.
export interface Portfolio {
  id: string
  name: string
  slug: string
  cover_image_url: string | null
  groups: LandingGroup[]
}

// Admin portfolio payload (GET /admin/portfolios) — raw content (groups hold ids).
export interface AdminPortfolio {
  id: string
  name: string
  slug: string
  cover_image_url: string | null
  is_active: boolean
  sort_order: number
  content: Record<string, any> | null
}

export interface CartItem {
  productId: string
  name: string
  sku: string
  price: number | null
  imageUrl: string | null
  quantity: number
}

export type OrderStatus =
  | 'new'
  | 'contacted'
  | 'confirmed'
  | 'shipped'
  | 'cancelled'

// Public order-tracking payload (GET /orders/track). No PII beyond line items.
export interface OrderTrack {
  reference: string
  status: OrderStatus
  total: string
  created_at: string
  items: OrderItem[]
  status_log: OrderStatusLogEntry[]
}

export interface CustomerDocument {
  url: string
  filename: string | null
  uploaded_at: string
}

// Customer account (panel).
export interface Customer {
  id: string
  phone: string
  full_name: string | null
  store_name: string | null
  verification_status: 'unverified' | 'pending' | 'approved' | 'rejected'
  verification_documents: CustomerDocument[]
  rejection_reason: string | null
}

export interface CustomerAddress {
  id: string
  title: string
  province: string
  city: string | null
  line: string
  is_default: boolean
}

export interface AdminOrder {
  id: string
  reference: string
  full_name: string
  phone: string
  store_name: string
  province: string
  city: string | null
  contact_method: 'call' | 'agent' | 'whatsapp'
  note: string | null // customer note
  internal_note: string | null // admin-only
  status: OrderStatus
  total: string
  is_read: boolean
  utm_source: string | null
  utm_medium: string | null
  utm_campaign: string | null
  referrer: string | null
  created_at: string
}

export interface OrderItem {
  product_id: string | null
  product_name: string
  unit_price: string | null
  quantity: number
}

export interface OrderStatusLogEntry {
  from_status: OrderStatus | null
  to_status: OrderStatus
  created_at: string
}

export interface AdminOrderDetail extends AdminOrder {
  items: OrderItem[]
  status_log: OrderStatusLogEntry[]
}

export interface OrderListResponse {
  items: AdminOrder[]
  total: number
  page: number
  page_size: number
  unread: number
}

// Admin customer view — mirrors backend CustomerAdminOut.
export interface CustomerAdmin {
  id: string
  phone: string
  full_name: string | null
  store_name: string | null
  verification_status: 'unverified' | 'pending' | 'approved' | 'rejected'
  verification_documents: CustomerDocument[]
  rejection_reason: string | null
  verified_at: string | null
  created_at: string
}

