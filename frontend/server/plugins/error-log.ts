/**
 * Nitro (SSR) error logging in the shared JSON contract shape, so SSR failures
 * land in Loki with the same fields as FastAPI logs (service=didar-web).
 */
export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('error', (error, { event } = {}) => {
    const line = {
      timestamp: new Date().toISOString(),
      level: 'ERROR',
      service: 'didar-web',
      env: process.env.NODE_ENV === 'production' ? 'production' : 'dev',
      module: 'nuxt.ssr',
      event: 'nuxt.ssr.error',
      message: String((error as Error)?.message ?? error),
      url: event?.path,
      error: {
        type: (error as Error)?.name,
        message: String((error as Error)?.message ?? error),
        stack: (error as Error)?.stack?.slice(0, 4000),
      },
    }
    console.error(JSON.stringify(line))
  })
})
