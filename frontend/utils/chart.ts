import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { toFa } from '~/utils/format'

let registered = false
// Register only what the dashboard uses (keeps the bundle lean).
export function registerCharts() {
  if (registered) return
  Chart.register(
    LineController,
    BarController,
    DoughnutController,
    LineElement,
    PointElement,
    BarElement,
    ArcElement,
    CategoryScale,
    LinearScale,
    Filler,
    Tooltip,
    Legend,
  )
  registered = true
}

// Brand palette (design tokens). Directional/status colours mirror STATUS_CLASS.
export const BRAND = {
  gold: '#B08A57',
  goldSoft: '#D9B985',
  navy: '#041E42',
  navySoft: 'rgba(4,30,66,0.55)',
  ink: '#041E42',
  inkMuted: 'rgba(4,30,66,0.55)',
  line: 'rgba(176,138,87,0.25)',
}

// Status → colour, aligned with the admin STATUS_CLASS chips.
export const STATUS_COLORS: Record<string, string> = {
  new: '#8A5B00', // warning
  contacted: '#7A8794', // neutral
  confirmed: '#1E7A46', // success
  shipped: '#0B9A55', // success (lighter)
  delivered: '#0E7A3E', // success (delivered)
  cancelled: '#B3261E', // danger
}

function reducedMotion() {
  return (
    import.meta.client &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

const faTicks = { callback: (v: unknown) => toFa(Number(v)) }

// Shared options: RTL, Persian digits on the value axis, quiet gridlines.
export function baseOptions(overrides: Record<string, unknown> = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: reducedMotion() ? false : { duration: 400 },
    plugins: {
      legend: { display: false },
      tooltip: {
        rtl: true,
        titleFont: { family: 'Doran' },
        bodyFont: { family: 'Doran' },
      },
    },
    ...overrides,
  }
}

export function categoryScales(horizontal = false) {
  const value = { beginAtZero: true, ticks: faTicks, grid: { color: BRAND.line } }
  const cat = { ticks: { color: BRAND.inkMuted }, grid: { display: false } }
  return horizontal ? { x: value, y: cat } : { x: cat, y: value }
}
