/**
 * Animate a product image from a source element into the floating cart bubble
 * (apple-design momentum feel, transform-only so it's compositor-friendly).
 * No-op under reduced-motion — the badge count still updates, which is the
 * actual feedback that matters.
 */
export function flyToCart(source: HTMLElement | null, imageUrl: string | null) {
  if (import.meta.server || !source || !imageUrl) return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const target = document.getElementById('cart-bubble')
  if (!target) return

  const from = source.getBoundingClientRect()
  const to = target.getBoundingClientRect()

  const clone = document.createElement('img')
  clone.src = imageUrl
  Object.assign(clone.style, {
    position: 'fixed',
    left: `${from.left}px`,
    top: `${from.top}px`,
    width: `${from.width}px`,
    height: `${from.height}px`,
    objectFit: 'cover',
    zIndex: '60',
    pointerEvents: 'none',
    borderRadius: '9999px',
  })
  document.body.appendChild(clone)

  const dx = to.left + to.width / 2 - (from.left + from.width / 2)
  const dy = to.top + to.height / 2 - (from.top + from.height / 2)

  clone
    .animate(
      [
        { transform: 'translate(0,0) scale(1)', opacity: 1 },
        { transform: `translate(${dx}px, ${dy}px) scale(0.15)`, opacity: 0.4 },
      ],
      { duration: 500, easing: 'cubic-bezier(0.2,0,0,1)' },
    )
    .addEventListener('finish', () => clone.remove())
}
