// First-party proxy for the Mautic tracker so its cookies are first-party (no
// Lighthouse "third-party cookies" penalty) while tracking keeps working.
//
// mtc.js bakes its origin into itself in two forms — a full `https://host` and a
// protocol-relative `location.protocol + '//host'`. We rewrite both to a
// root-relative `/mtc/...` so every downstream call (mtracking.gif, mtc/event,
// forms) routes back through this proxy as same-origin, and cookieDomainRewrite
// makes the Set-Cookie first-party.
export default defineEventHandler(async (event) => {
  const origin = useRuntimeConfig(event).mauticOrigin as string
  const sub = event.path.replace(/^\/mtc/, '')
  const target = origin + sub

  if (sub.startsWith('/mtc.js')) {
    const host = new URL(origin).host
    const esc = host.replace(/\./g, '\\.')
    const js = (await $fetch<string>(target, { responseType: 'text' }))
      // `(…protocol…) + '//host` → `'/mtc` (drop the forced-protocol prefix)
      .replace(new RegExp(`\\([^()]*protocol[^()]*\\)\\s*\\+\\s*'//${esc}`, 'g'), "'/mtc")
      .split(origin).join('/mtc') // full `https://host` literals
      .split(`//${host}`).join('/mtc') // any residual protocol-relative literal
    setResponseHeader(event, 'content-type', 'application/javascript; charset=utf-8')
    return js
  }

  return proxyRequest(event, target, { cookieDomainRewrite: '' })
})
