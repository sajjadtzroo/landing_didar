/**
 * Capture UTM params + referrer into sessionStorage on landing, so they can be
 * sent with the order and stored on the row — the sales team keeps the source
 * even if Matomo was blocked. Only writes on first landing of the session.
 */
export interface Attribution {
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  referrer?: string
}

const KEY = 'didar_attribution'

export function readAttribution(): Attribution {
  if (import.meta.server) return {}
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || '{}')
  } catch {
    return {}
  }
}

export default defineNuxtPlugin(() => {
  if (sessionStorage.getItem(KEY)) return
  const params = new URLSearchParams(location.search)
  const data: Attribution = {
    utm_source: params.get('utm_source') || undefined,
    utm_medium: params.get('utm_medium') || undefined,
    utm_campaign: params.get('utm_campaign') || undefined,
    referrer: document.referrer || undefined,
  }
  sessionStorage.setItem(KEY, JSON.stringify(data))
})
