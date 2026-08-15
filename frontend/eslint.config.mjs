// ESLint 9 flat config. Uses the standalone Nuxt preset (@nuxt/eslint-config),
// which wires up eslint-plugin-vue + typescript-eslint recommended rules with
// Nuxt-aware defaults (auto-import globals, pages/layouts single-word names).
// Stylistic/formatting rules stay off — formatting is not linted here.
import { createConfigForNuxt } from '@nuxt/eslint-config/flat'

export default createConfigForNuxt({
  features: {
    stylistic: false,
  },
}).append(
  {
    ignores: [
      '.nuxt/**',
      '.output/**',
      'dist/**',
      'node_modules/**',
      'public/**',
      'coverage/**',
    ],
  },
  {
    rules: {
      // Real-world API payloads flow through `any` in a few typed boundaries;
      // tightening these is stage-2 work, not a lint gate.
      '@typescript-eslint/no-explicit-any': 'off',
      // Purely stylistic template preferences — not worth churning ~35
      // components over. Revisit with a formatter, not the linter.
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',
      'vue/first-attribute-linebreak': 'off',
    },
  },
)
