import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Mirror Nuxt's path aliases (srcDir = project root) so stores/utils import
// cleanly without a Nuxt runtime. Tests run in happy-dom for localStorage etc.
const r = (p: string) => fileURLToPath(new URL(p, import.meta.url))

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '~~': r('.'),
      '@@': r('.'),
      '~': r('.'),
      '@': r('.'),
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['tests/**/*.spec.ts'],
  },
})
