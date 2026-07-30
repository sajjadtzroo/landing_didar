/**
 * Lead capture into Mautic. Pushes contact fields to the global `mt` tracker so
 * the visitor is identified/updated as a Mautic contact (no API creds needed —
 * uses the same public tracking as the pageview pixel). SSR-guarded.
 *
 * Mautic field aliases used: firstname, phone, company, state, city, tags.
 */
export function useMautic() {
  const identify = (fields: Record<string, string | undefined | null>) => {
    if (import.meta.server || typeof window.mt !== 'function') return
    const clean = Object.fromEntries(
      Object.entries(fields).filter(([, v]) => v),
    )
    window.mt('send', 'pageview', clean)
  }
  return { identify }
}
