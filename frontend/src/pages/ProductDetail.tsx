import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type Product } from '../api'
import CompleteTheLook from '../components/CompleteTheLook'
import SaveButtons from '../components/SaveButtons'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setProduct(null)
    setError('')
    fetchProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message === 'Not found' ? "We couldn't find that product." : "We couldn't load this product."))
  }, [productId])

  if (error)
    return (
      <>
        <Link to="/products" className="back">
          ← Back to products
        </Link>
        <p className="error">{error}</p>
      </>
    )
  if (!product) return <p className="muted">Loading…</p>

  return (
    <>
      <Link to="/products" className="back">
        ← Back to products
      </Link>
      <article className="detail">
        <div className="detail-img">
          <img src={product.image_url_large} alt={product.name} width={800} height={800} />
        </div>
        <div className="detail-info">
          <div className="card-type">{product.garment_type}</div>
          <h1>{product.name}</h1>
          <div className="detail-price">{formatPrice(product.price)}</div>
          <p className="detail-desc">{product.description}</p>

          <h2 className="detail-label">Colors</h2>
          <div className="chips">
            {product.colors.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>

          <h2 className="detail-label">Sizes &amp; availability</h2>
          {product.inventory.length === 0 ? (
            <p className="muted">Size information isn't available for this item.</p>
          ) : (
            <ul className="sizes">
              {product.inventory.map(({ size, quantity }) => (
                <li key={size} className={quantity === 0 ? 'out' : quantity <= LOW_STOCK ? 'low' : ''}>
                  <span className="size">{size}</span>
                  <span className="stock">{quantity === 0 ? 'Sold out' : quantity <= LOW_STOCK ? `Only ${quantity} left` : `${quantity} in stock`}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="muted small">{product.total_stock} total in stock across all sizes.</p>
          <SaveButtons product={product} />
        </div>
      </article>
      <CompleteTheLook productId={product.product_id} productName={product.name} />
    </>
  )
}
