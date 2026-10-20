import { useCallback, useEffect, useState } from 'react'
import { fetchList, moveToCloset, removeFromList, type ListItem } from '../api'
import { useAuth } from '../auth-context'
import LoginPrompt from '../components/LoginPrompt'
import ProductCard from '../components/ProductCard'

/** Wish List (Problem 9): items saved for later, with live price and stock. */
export default function Wishlist() {
  const { user, loading } = useAuth()
  const [items, setItems] = useState<ListItem[] | null>(null)
  const [message, setMessage] = useState('')

  const load = useCallback(() => {
    fetchList('wishlist')
      .then(setItems)
      .catch(() => setItems([]))
  }, [])

  useEffect(() => {
    if (user) load()
  }, [user, load])

  async function remove(id: number) {
    await removeFromList('wishlist', id)
    load()
  }

  async function bought(i: ListItem) {
    await moveToCloset(i.id)
    setMessage(`Moved ${i.product.name} to your closet. Enjoy it!`)
    load()
  }

  if (loading) return null
  if (!user)
    return (
      <>
        <h1>Wish List</h1>
        <LoginPrompt what="a wish list" />
      </>
    )

  const total = (items ?? []).reduce((sum, i) => sum + i.product.price, 0)

  return (
    <>
      <div className="section-head">
        <h1>Wish List</h1>
        {items && items.length > 0 && (
          <span className="muted">
            {items.length} {items.length === 1 ? 'item' : 'items'} · ${total.toFixed(2)} total
          </span>
        )}
      </div>
      <p className="muted lead-in">Saved for later. Prices and stock are live, so you'll see right away if your size sells out.</p>
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      {items && items.length === 0 && (
        <div className="empty">
          <p>
            Nothing saved yet. Open any product and click <strong>“♡ Save to wish list”</strong>, or ask the chat assistant to
            add it for you.
          </p>
        </div>
      )}
      <div className="grid">
        {items?.map((i) => {
          const status =
            i.size && i.size_status === 'sold out' ? (
              <span className="status-out">Size {i.size} is sold out</span>
            ) : i.size ? (
              <span className="status-in">Size {i.size} in stock</span>
            ) : i.product.total_stock === 0 ? (
              <span className="status-out">Sold out</span>
            ) : (
              <span className="status-in">In stock: {i.product.sizes_in_stock.join(' ')}</span>
            )
          return (
            <ProductCard
              key={i.id}
              product={i.product}
              note={status}
              actions={
                <>
                  <button className="btn-small primary" onClick={() => bought(i)}>
                    I bought it
                  </button>
                  <button className="btn-small" onClick={() => remove(i.id)}>
                    Remove
                  </button>
                </>
              }
            />
          )
        })}
      </div>
    </>
  )
}
