// Small celebratory button effects (Problem 10). DOM-only, no libraries, and
// skipped entirely for shoppers who ask their OS for reduced motion.

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const CONFETTI_COLORS = ['#00356b', '#286dc0', '#4a9bff', '#ffc72c', '#ffffff']

/** Pieces fly out from the center of `el`: confetti by default, or an emoji (e.g. '♥'). */
export function burst(from: Element | DOMRect | null | undefined, opts: { emoji?: string; count?: number; spread?: number } = {}) {
  if (!from || reducedMotion()) return
  const { emoji, count = emoji ? 10 : 26, spread = emoji ? 70 : 140 } = opts
  const r = from instanceof Element ? from.getBoundingClientRect() : from // a saved rect works after the element is gone
  const cx = r.left + r.width / 2
  const cy = r.top + r.height / 2
  for (let i = 0; i < count; i++) {
    const piece = document.createElement('span')
    piece.className = emoji ? 'fx-emoji' : 'fx-confetti'
    if (emoji) piece.textContent = emoji
    else piece.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length]
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.6
    const dist = spread * (0.5 + Math.random() * 0.6)
    piece.style.left = `${cx}px`
    piece.style.top = `${cy}px`
    document.body.appendChild(piece)
    const duration = 700 + Math.random() * 500
    piece.animate(
        [
          { transform: 'translate(-50%, -50%) scale(.6) rotate(0deg)', opacity: 1 },
          {
            transform: `translate(calc(-50% + ${Math.cos(angle) * dist}px), calc(-50% + ${Math.sin(angle) * dist + (emoji ? -20 : 40)}px)) scale(1) rotate(${Math.random() * 540 - 270}deg)`,
            opacity: 0,
          },
        ],
        { duration, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'forwards' },
      )
    // A timer, not animation.finished: that promise never settles in a background tab.
    window.setTimeout(() => piece.remove(), duration + 50)
  }
}

/** A copy of the product photo flies into the bag icon in the nav bar. */
export function flyToBag(img: HTMLImageElement | null) {
  const bag = document.getElementById('bag-button')
  if (!img || !bag || reducedMotion()) return
  const from = img.getBoundingClientRect()
  const to = bag.getBoundingClientRect()
  const clone = img.cloneNode() as HTMLImageElement
  clone.className = 'fx-fly'
  Object.assign(clone.style, { left: `${from.left}px`, top: `${from.top}px`, width: `${from.width}px`, height: `${from.height}px` })
  document.body.appendChild(clone)
  const dx = to.left + to.width / 2 - (from.left + from.width / 2)
  const dy = to.top + to.height / 2 - (from.top + from.height / 2)
  clone.animate(
      [
        { transform: 'translate(0,0) scale(1)', opacity: 0.95, borderRadius: '16px' },
        { transform: `translate(${dx * 0.6}px, ${dy * 0.6 - 60}px) scale(.45)`, opacity: 0.9, offset: 0.6 },
        { transform: `translate(${dx}px, ${dy}px) scale(.08)`, opacity: 0.3, borderRadius: '50%' },
      ],
      { duration: 750, easing: 'cubic-bezier(.5,0,.7,1)', fill: 'forwards' },
    )
  window.setTimeout(() => {
    clone.remove()
    bag.classList.remove('pop')
    void (bag as HTMLElement).offsetWidth // restart the CSS animation
    bag.classList.add('pop')
  }, 760)
}

/** Gentle shake to point at something the shopper still needs to do (e.g. pick a size). */
export function nudge(el: Element | null) {
  if (!el || reducedMotion()) return
  el.animate(
    [{ transform: 'translateX(0)' }, { transform: 'translateX(-6px)' }, { transform: 'translateX(6px)' }, { transform: 'translateX(-4px)' }, { transform: 'translateX(0)' }],
    { duration: 380 },
  )
}
