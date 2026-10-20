import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type CardProduct } from '../api'

// Used for the catalogue grid, chat results, closet, wish list and recommendations.
// Every card links to the same single-item page, /products/:productId.
// Images are the compressed 360 px card versions (Problem 9).
export default function ProductCard({ product, note, actions }: { product: CardProduct; note?: ReactNode; actions?: ReactNode }) {
  const soldOut = product.total_stock === 0
  const card = (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-img">
        <img src={product.image_url} alt={product.name} loading="lazy" width={360} height={360} />
      </div>
      <div className="card-body">
        <div className="card-type">{product.garment_type}</div>
        <h3 className="card-name">{product.name}</h3>
        <p className="card-desc">{product.description}</p>
        {note && <p className="card-note">{note}</p>}
        <div className="card-price">
          {formatPrice(product.price)}
          {soldOut && <span className="badge-out">Sold out</span>}
        </div>
      </div>
    </Link>
  )
  if (!actions) return card
  return (
    <div className="card-shell">
      {card}
      <div className="card-actions">{actions}</div>
    </div>
  )
}
