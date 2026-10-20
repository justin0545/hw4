import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'
import ProductCard from './ProductCard'

/**
 * A product card that opens a sneak-peek panel on hover (Problem 10): bigger
 * photo, full description, price and every size (sold-out ones struck through),
 * so shoppers can size up top items before clicking. Mouse only; on touch the
 * card just opens the product page.
 */
export default function PeekCard({ product }: { product: Product }) {
  const [open, setOpen] = useState(false)
  const [flip, setFlip] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const ref = useRef<HTMLDivElement>(null)

  function enter(e: React.PointerEvent) {
    if (e.pointerType !== 'mouse') return
    const r = ref.current?.getBoundingClientRect()
    setFlip(!!r && r.right + 320 > window.innerWidth)
    timer.current = window.setTimeout(() => setOpen(true), 280)
  }
  function leave() {
    window.clearTimeout(timer.current)
    setOpen(false)
  }

  const low = product.inventory.filter((s) => s.quantity > 0 && s.quantity <= 5).map((s) => s.size)

  return (
    <div ref={ref} className="peek-wrap" onPointerEnter={enter} onPointerLeave={leave}>
      <ProductCard product={product} />
      <div className={`peek${open ? ' open' : ''}${flip ? ' flip' : ''}`} aria-hidden={!open}>
        <span className="peek-ribbon">👀 Sneak peek</span>
        <img src={product.image_url_large} alt="" width={300} height={300} loading="lazy" />
        <div className="peek-body">
          <span className="card-type">{product.garment_type}</span>
          <strong className="peek-name">{product.name}</strong>
          <span className="peek-price">{formatPrice(product.price)}</span>
          <p>{product.description}</p>
          <div className="peek-sizes">
            {product.inventory.map((s) => (
              <span key={s.size} className={s.quantity === 0 ? 'out' : s.quantity <= 5 ? 'low' : ''}>
                {s.size}
              </span>
            ))}
          </div>
          {low.length > 0 && <span className="peek-low">🔥 Almost gone in {low.join(', ')}</span>}
          <Link to={`/products/${product.product_id}`} className="btn btn-small-cta" tabIndex={open ? 0 : -1}>
            View details →
          </Link>
        </div>
      </div>
    </div>
  )
}
