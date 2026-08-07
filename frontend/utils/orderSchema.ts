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
  store_name: z
    .string()
    .trim()
    .min(2, CONTENT.form.errors.storeName)
    .max(80, CONTENT.form.errors.storeName),
  province: z.enum(provinceValues, { message: CONTENT.form.errors.province }),
  city: z.string().max(60).optional().or(z.literal('')),
  contact_method: z.enum(['call', 'agent', 'whatsapp']).default('call'),
  note: z.string().max(300, CONTENT.form.errors.note).optional().or(z.literal('')),
})

export type OrderFormValues = z.infer<typeof orderSchema>
