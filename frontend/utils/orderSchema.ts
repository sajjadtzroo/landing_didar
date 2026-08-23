import { z } from 'zod'
import { CONTENT } from '~/constants/content'
import { PROVINCES } from '~/constants/provinces'

const provinceValues = PROVINCES.map((p) => p.value) as [string, ...string[]]

// Mirrors the server Pydantic rules exactly (server is the source of truth).
export const orderSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(3, CONTENT.form.errors.fullName)
    .max(60, CONTENT.form.errors.fullName),
  phone: z.string().regex(/^09\d{9}$/, CONTENT.form.errors.phone),
  // Only name + phone are required; the rest just speed the follow-up call.
  store_name: z.string().trim().max(80, CONTENT.form.errors.storeName).optional().or(z.literal('')),
  province: z.enum(provinceValues, { message: CONTENT.form.errors.province }).or(z.literal('')).optional(),
  city: z.string().max(60).optional().or(z.literal('')),
  contact_method: z.enum(['call', 'agent', 'whatsapp']).default('call'),
  note: z.string().max(300, CONTENT.form.errors.note).optional().or(z.literal('')),
})

export type OrderFormValues = z.infer<typeof orderSchema>
