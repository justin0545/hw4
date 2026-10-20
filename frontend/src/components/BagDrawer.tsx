import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import { useCart } from '../cart-context'
import { burst } from '../effects'
import Bulldog from './Bulldog'

/** Slide-in shopping bag with a celebratory checkout (Problem 10). */
export default function BagDrawer() {
  const { items, count, total, open, setOpen, setQty, remove, clear } = useCart()
  const [done, setDone] = useState(false)
  const checkoutRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) setDone(false)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, setOpen])

  function checkout() {
    // Save the button's position first: it's replaced by the success panel right away.
    const at = checkoutRef.current?.getBoundingClientRect()
    burst(at, { count: 60, spread: 260 })
    setTimeout(() => burst(at, { emoji: '🐾', count: 12, spread: 160 }), 250)
    setDone(true)
  }

  return (
    <>
      <div className={`bag-scrim${open ? ' open' : ''}`} onClick={() => setOpen(false)} />
      <aside className={`bag${open ? ' open' : ''}`} aria-label="Shopping bag" aria-hidden={!open}>
        <header className="bag-head">
          <h2>Your bag {count > 0 && <span className="bag-count-pill">{count}</span>}</h2>
          <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close bag">
            ×
          </button>
        </header>

        {done ? (
          <div className="bag-done">
            <Bulldog size={110} mood="wink" className="bob" />
            <h3>Boola Boola, you're all set! 🎉</h3>
            <p>
              Your {count} {count === 1 ? 'item is' : 'items are'} locked in ({formatPrice(total)}). Online payment is launching soon. Show this bag at the
              Campus Customs counter, or keep it here for later.
            </p>
            <button className="btn" onClick={() => setOpen(false)}>
              Keep shopping
            </button>
            <button className="btn-link" onClick={() => { clear(); setOpen(false) }}>
              Clear bag
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="bag-empty">
            <Bulldog size={90} />
            <p>Your bag is empty. Let's fix that!</p>
            <Link to="/products" className="btn" onClick={() => setOpen(false)}>
              Shop spirit gear
            </Link>
          </div>
        ) : (
          <>
            <ul className="bag-items">
              {items.map((i) => (
                <li key={i.key}>
                  <img src={i.image_url} alt="" width={64} height={64} />
                  <div className="bag-info">
                    <Link to={`/products/${i.product_id}`} onClick={() => setOpen(false)}>
                      {i.name}
                    </Link>
                    <span className="muted small">Size {i.size}</span>
                    <div className="qty">
                      <button onClick={() => setQty(i.key, i.qty - 1)} aria-label="One fewer">−</button>
                      <span>{i.qty}</span>
                      <button onClick={() => setQty(i.key, i.qty + 1)} aria-label="One more">+</button>
                      <button className="btn-link" onClick={() => remove(i.key)}>Remove</button>
                    </div>
                  </div>
                  <strong>{formatPrice(i.price * i.qty)}</strong>
                </li>
              ))}
            </ul>
            <footer className="bag-foot">
              <div className="bag-total">
                <span>Subtotal</span>
                <strong>{formatPrice(total)}</strong>
              </div>
              <button ref={checkoutRef} className="btn btn-checkout" onClick={checkout}>
                Check out · {formatPrice(total)}
              </button>
              <p className="muted small center">No surprises: prices and sizes are live from our inventory.</p>
            </footer>
          </>
        )}
      </aside>
    </>
  )
}
