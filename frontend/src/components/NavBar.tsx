import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { fetchProductsCached, formatPrice, type Product } from '../api'
import { useAuth } from '../auth-context'
import { useCart } from '../cart-context'
import { CATEGORIES, TOP_PICKS } from '../shop'
import Bulldog from './Bulldog'

/** "Shop" hover menu: categories on the left, sneak peeks of top items on the right (Problem 10). */
function ShopMenu() {
  const [top, setTop] = useState<Product[]>([])
  const [peek, setPeek] = useState<Product | null>(null)
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    fetchProductsCached()
      .then((all) => {
        const picks = TOP_PICKS.slice(0, 4).map((id) => all.find((p) => p.product_id === id)).filter((p): p is Product => !!p)
        setTop(picks)
        setPeek(picks[0] ?? null)
      })
      .catch(() => undefined)
  }, [])

  useEffect(() => setOpen(false), [location.pathname, location.search])

  return (
    <div className={`shop-menu${open ? ' open' : ''}`} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <NavLink to="/products" className="shop-trigger">
        Products
      </NavLink>
      <button className="caret" aria-expanded={open} aria-label="Show shop menu" onClick={() => setOpen((o) => !o)}>
        ▾
      </button>
      <div className="shop-panel" role="menu">
        <div className="shop-cats">
          <span className="shop-label">Categories</span>
          {CATEGORIES.map((c) => (
            <Link key={c.key} to={`/products?type=${c.key}`} role="menuitem">
              <strong>{c.label}</strong>
              <span>{c.blurb}</span>
            </Link>
          ))}
          <Link to="/products" className="shop-all" role="menuitem">
            Shop all 102 items →
          </Link>
        </div>
        <div className="shop-top">
          <span className="shop-label">Top picks · hover for a sneak peek</span>
          <div className="shop-top-list">
            {top.map((p) => (
              <Link key={p.product_id} to={`/products/${p.product_id}`} className={peek?.product_id === p.product_id ? 'on' : ''} onMouseEnter={() => setPeek(p)} onFocus={() => setPeek(p)}>
                <img src={p.image_url} alt="" width={48} height={48} />
                <span>{p.name}</span>
              </Link>
            ))}
          </div>
        </div>
        {peek && (
          <Link to={`/products/${peek.product_id}`} className="shop-peek" key={peek.product_id}>
            <img src={peek.image_url_large} alt={peek.name} width={220} height={220} />
            <strong>{peek.name}</strong>
            <span className="shop-peek-price">{formatPrice(peek.price)}</span>
            <span className="shop-peek-sizes">
              {peek.inventory.map((s) => (
                <i key={s.size} className={s.quantity === 0 ? 'out' : ''}>
                  {s.size}
                </i>
              ))}
            </span>
          </Link>
        )}
      </div>
    </div>
  )
}

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const { count, setOpen } = useCart()
  const navigate = useNavigate()

  async function onLogout() {
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav-inner">
        <NavLink to="/" className="brand" aria-label="Campus Customs home">
          <Bulldog size={40} className="brand-dog" />
          <span>
            <span className="brand-name">Campus Customs</span>
            <span className="brand-tag">Yale spirit apparel</span>
          </span>
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/" end>
            Home
          </NavLink>
          <ShopMenu />
          <NavLink to="/about">About Us</NavLink>
          <span className="nav-sep" />
          {loading ? null : user ? (
            <>
              <NavLink to="/closet">My Closet</NavLink>
              <NavLink to="/wishlist">♡ Wish List</NavLink>
              <span className="nav-user">Hi, {user.first_name}</span>
              <button className="nav-btn" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/create-account" className="nav-cta">
                Create Account
              </NavLink>
            </>
          )}
          <button id="bag-button" className="bag-btn" onClick={() => setOpen(true)} aria-label={`Shopping bag, ${count} items`}>
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
              <path d="M6 8h12l-1 12H7L6 8zm3 0V6a3 3 0 0 1 6 0v2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            </svg>
            {count > 0 && <span className="bag-badge">{count}</span>}
          </button>
        </nav>
      </div>
    </header>
  )
}
