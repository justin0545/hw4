import { useEffect, useState } from 'react'
import type { ChatProduct } from '../api'
import { useAuth } from '../auth-context'
import { openStylist } from '../shop'
import ProductCard from './ProductCard'

interface Piece {
  product: ChatProduct
  role: string
  tip: string
  why_it_matches: string
  already_owned: boolean
}

/** "Complete the look" on the product page (Problem 10): the same outfit logic the chat stylist uses. */
export default function CompleteTheLook({ productId, productName }: { productId: string; productName: string }) {
  const { user } = useAuth()
  const [pieces, setPieces] = useState<Piece[]>([])

  useEffect(() => {
    fetch(`/api/products/${productId}/outfit`)
      .then((r) => (r.ok ? r.json() : { pieces: [] }))
      .then((d) => setPieces(d.pieces))
      .catch(() => setPieces([]))
  }, [productId, user?.id])

  if (pieces.length === 0) return null
  return (
    <section className="look">
      <div className="section-head">
        <h2>Complete the look</h2>
        <button className="btn-link" onClick={() => openStylist(`How should I style the ${productName}?`)}>
          💬 Ask the Stylist how to wear it
        </button>
      </div>
      <div className="grid">
        {pieces.map((p) => (
          <ProductCard
            key={p.product.product_id}
            product={p.product}
            note={
              <>
                {p.already_owned ? '✓ Already in your closet. ' : ''}
                {p.tip} <span className="match">· {p.why_it_matches}</span>
              </>
            }
          />
        ))}
      </div>
    </section>
  )
}
