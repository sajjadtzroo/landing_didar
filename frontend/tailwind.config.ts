import type { Config } from 'tailwindcss'

/**
 * Didar Gold tokens (from DESIGN_SYSTEM copy.md).
 * - Brand constants: static hex → support /opacity modifiers.
 * - Theme-aware tokens: CSS variables resolved per [data-theme] (see main.css).
 * - Sharp by design: all radii = 0, only `full` = 9999px.
 */
export default <Partial<Config>>{
  content: [],
  theme: {
    // Brand is square-cornered. Override the whole scale to 0; keep `full`.
    borderRadius: {
      none: '0',
      sm: '0',
      DEFAULT: '0',
      md: '0',
      lg: '0',
      xl: '0',
      '2xl': '0',
      '3xl': '0',
      full: '9999px',
    },
    extend: {
      colors: {
        // Brand constants (identical both themes)
        gold: '#B08A57',
        'gold-soft': '#D9B985',
        navy: '#041E42',
        'navy-deep': '#020B17',
        cream: '#F7F3EE',
        'cream-bright': '#FFFCF7',
        'danger-bright': '#FFB4AB',

        // Theme-aware semantic tokens (var-backed; no /opacity — pre-resolved)
        surface: 'var(--surface)',
        'surface-soft': 'var(--surface-soft)',
        'surface-raised': 'var(--surface-raised)',
        ink: 'var(--ink)',
        'ink-muted': 'var(--ink-muted)',
        'gold-text': 'var(--gold-text)',
        line: 'var(--line)',
        header: 'var(--header)',
        'media-surface': 'var(--media-surface)',
        footer: 'var(--footer)',

        // Status (AA-tuned per theme)
        danger: 'var(--danger)',
        'danger-soft': 'var(--danger-soft)',
        success: 'var(--success)',
        'success-soft': 'var(--success-soft)',
        warning: 'var(--warning)',
        'warning-soft': 'var(--warning-soft)',
      },
      fontFamily: {
        sans: ['Doran', 'Vazirmatn', 'system-ui', 'sans-serif'],
      },
      maxWidth: {
        content: '1280px',
        hero: '1450px',
        wide: '1800px',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
      },
      boxShadow: {
        luxury: '0 24px 65px rgba(4,30,66,0.16)',
      },
    },
  },
}
