import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { addToList, fetchList, type ListItem, type ListKind, type Product } from '../api'
import { useAuth } from '../auth-context'
import { useCart } from '../cart-context'
import { burst, flyToBag, nudge } from '../effects'

/**
 * Product page actions: pick a size, then Add to bag (Problem 10), Save to wish
 * list or "I own this" (Problem 9). Each has its own little celebration.
 */
export default function SaveButtons({ product }: { product: Product }) {
  const { user } = useAuth()
  const cart = useCart()
  const [size, setSize] = useState('')
  const [lists, setLists] = useState<Record<ListKind, ListItem[]>>({ closet: [], wishlist: [] })
  const [message, setMessage] = useState('')
  const sizeRef = useRef<HTMLDivElement>(null)
  const wishRef = useRef<HTMLButtonElement>(null)
  const ownRef = useRef<HTMLButtonElement>(null)

  const load = useCallback(async () => {
    const [closet, wishlist] = await Promise.all([fetchList('closet'), fetchList('wishlist')])
    setLists({ closet, wishlist })
  }, [])

  useEffect(() => {
    setMessage('')
    setSize('')
    if (user) load().catch(() => undefined)
  }, [user, product.product_id, load])

  const saved = (kind: ListKind) => lists[kind].filter((i) => i.product.product_id === product.product_id)
  const describe = (items: ListItem[]) => items.map((i) => i.size ?? 'any size').join(', ')
  const qty = product.inventory.find((s) => s.size === size)?.quantity ?? 0

  function addToBag() {
    if (!size) {
      setMessage('Pick your size first 👆')
      nudge(sizeRef.current)
      return
    }
    cart.add({ product_id: product.product_id, name: product.name, price: product.price, image_url: product.image_url, size })
    flyToBag(document.querySelector<HTMLImageElement>('.detail-img img'))
    setMessage(`Added ${product.name} (${size}) to your bag!`)
  }

  async function save(kind: ListKind) {
    try {
      await addToList(kind, product.product_id, size || null)
      await load()
      if (kind === 'wishlist') burst(wishRef.current, { emoji: '♥', count: 12 })
      else burst(ownRef.current, { emoji: '🐾', count: 8 })
      setMessage(kind === 'wishlist' ? 'Saved to your wish list ♥' : 'Added to your closet!')
    } catch (err) {
      setMessage((err as Error).message)
    }
  }

  return (
    <div className="save-box">
      <div className="size-picker" ref={sizeRef} role="radiogroup" aria-label="Size">
        {product.inventory.map((s) => (
          <button
            key={s.size}
            role="radio"
            aria-checked={size === s.size}
            disabled={s.quantity === 0}
            className={`size-opt${size === s.size ? ' on' : ''}`}
            onClick={() => setSize(s.size)}
            title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
          >
            {s.size}
          </button>
        ))}
      </div>
      {size && qty > 0 && qty <= 5 && <p className="hurry">🔥 Only {qty} left in {size}</p>}
      <button className="btn btn-bag" onClick={addToBag} disabled={product.total_stock === 0}>
        {product.total_stock === 0 ? 'Sold out' : 'Add to bag'}
      </button>
      {user ? (
        <div className="save-actions">
          <button ref={wishRef} className="btn btn-ghost" onClick={() => save('wishlist')}>
            ♡ Save to wish list
          </button>
          <button ref={ownRef} className="btn btn-ghost" onClick={() => save('closet')}>
            I own this
          </button>
        </div>
      ) : (
        <p className="muted small save-login">
          <Link to="/login">Log in</Link> to save this to your wish list or closet.
        </p>
      )}
      {message && (
        <p className="save-msg" role="status">
          {message}
        </p>
      )}
      {saved('wishlist').length > 0 && (
        <p className="small">
          ♥ On your <Link to="/wishlist">wish list</Link> ({describe(saved('wishlist'))})
        </p>
      )}
      {saved('closet').length > 0 && (
        <p className="small">
          ✓ In your <Link to="/closet">closet</Link> ({describe(saved('closet'))})
        </p>
      )}
    </div>
  )
}
