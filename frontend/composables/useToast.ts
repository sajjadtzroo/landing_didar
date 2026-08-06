/**
 * Minimal global toast queue (useState so any component can push). One host
 * (<AppToast>) renders them in an aria-live region. Auto-dismiss ~3.5s.
 * ponytail: no severity/position config until a second kind of toast needs it.
 */
export interface Toast {
  id: number
  message: string
}

let seq = 0

export function useToast() {
  const toasts = useState<Toast[]>('ui-toasts', () => [])

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function toast(message: string) {
    const id = ++seq
    toasts.value = [...toasts.value, { id, message }]
    if (import.meta.client) {
      setTimeout(() => dismiss(id), 3500)
    }
  }

  return { toasts, toast, dismiss }
}
