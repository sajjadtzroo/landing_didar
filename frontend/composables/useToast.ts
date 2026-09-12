/**
 * Minimal global toast queue (useState so any component can push). One host
 * (<AppToast>) renders them in an aria-live region. Auto-dismiss ~3.5s
 * (errors linger ~5s so they can be read).
 */
export interface Toast {
  id: number
  message: string
  kind: 'success' | 'error'
}

let seq = 0

export function useToast() {
  const toasts = useState<Toast[]>('ui-toasts', () => [])

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function toast(message: string, kind: 'success' | 'error' = 'success') {
    const id = ++seq
    toasts.value = [...toasts.value, { id, message, kind }]
    if (import.meta.client) {
      setTimeout(() => dismiss(id), kind === 'error' ? 5000 : 3500)
    }
  }

  return { toasts, toast, dismiss }
}
