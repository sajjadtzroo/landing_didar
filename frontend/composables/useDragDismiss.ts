import { ref } from 'vue'

/**
 * Drag-to-dismiss for a bottom sheet / drawer (apple-design §2b).
 * 1:1 finger tracking via Pointer Events; on release, project momentum
 * (Apple's exponential-decay formula) and decide dismiss vs snap-back.
 * Interruptible — a new pointerdown grabs it again. Respects reduced-motion by
 * skipping the drag entirely (the backdrop tap / close button still work).
 */
export function useDragDismiss(onDismiss: () => void) {
  const offset = ref(0) // px translated along the dismiss axis (>=0)
  const dragging = ref(false)

  let startY = 0
  let lastY = 0
  let lastT = 0
  let velocity = 0 // px/s
  let height = 0
  let reduced = false

  function project(v: number, decel = 0.998) {
    return (v / 1000) * decel / (1 - decel)
  }

  function down(e: PointerEvent) {
    reduced =
      import.meta.client &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) return
    const el = e.currentTarget as HTMLElement
    height = el.getBoundingClientRect().height || window.innerHeight
    el.setPointerCapture(e.pointerId)
    dragging.value = true
    startY = lastY = e.clientY
    lastT = e.timeStamp
    velocity = 0
  }

  function move(e: PointerEvent) {
    if (!dragging.value) return
    const dy = e.clientY - startY
    // Only track downward drag; rubber-band any upward pull.
    offset.value = dy > 0 ? dy : dy * 0.2
    const dt = e.timeStamp - lastT
    if (dt > 0) velocity = ((e.clientY - lastY) / dt) * 1000
    lastY = e.clientY
    lastT = e.timeStamp
  }

  function up() {
    if (!dragging.value) return
    dragging.value = false
    const projected = offset.value + project(velocity)
    if (projected > height * 0.4) {
      offset.value = height // let the transition slide it out
      onDismiss()
    } else {
      offset.value = 0 // snap back
    }
  }

  function reset() {
    offset.value = 0
    dragging.value = false
  }

  return { offset, dragging, down, move, up, reset }
}
