import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProductsCached, type Product } from '../api'
import Bulldog from '../components/Bulldog'
import PeekCard from '../components/PeekCard'
import RecommendedForYou from '../components/RecommendedForYou'
import Reveal from '../components/Reveal'
import { CATEGORIES, TOP_PICKS, openStylist } from '../shop'

const QUOTES = ['Proudly show your Yale pride!', 'Every day is spirit day!', 'Boola Boola, from head to toe!']
const TICKER = ['Boola Boola', 'Every day is spirit day', 'Bulldogs!', 'Beat Harvard', 'Proudly show your Yale pride', 'Go Elis']

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchProductsCached()
      .then(setProducts)
      .catch(() => setProducts([]))
  }, [])

  const byId = (id: string) => products.find((p) => p.product_id === id)
  const top = TOP_PICKS.map(byId).filter((p): p is Product => !!p)
  const floaters = ['district-vit-hoodie-vintage-bulldog', '2025-yale-vs-harvard-t-shirt', 'branford-1-4-zip'].map(byId).filter((p): p is Product => !!p)

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-kicker">New Haven's go-to for Yale spirit apparel</p>
          <h1>
            Proudly show your <span className="hero-accent">Yale pride!</span>
          </h1>
          <p className="hero-sub">Every day is spirit day. Hoodies, crewnecks, tees and jackets for students, alumni and the biggest Bulldog fans.</p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-gold">
              Shop the collection
            </Link>
            <button className="btn btn-ghost-light" onClick={() => openStylist()}>
              💬 Ask our Stylist
            </button>
          </div>
          <ul className="hero-points">
            <li>102 styles</li>
            <li>Live size &amp; stock</li>
            <li>A stylist in every chat</li>
          </ul>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="hero-ring" />
          <Bulldog size={260} className="hero-dog" />
          {floaters.map((p, i) => (
            <Link key={p.product_id} to={`/products/${p.product_id}`} className={`floater f${i}`} tabIndex={-1}>
              <img src={p.image_url} alt="" width={110} height={110} />
            </Link>
          ))}
        </div>
      </section>

      <div className="ticker" aria-hidden="true">
        <div className="ticker-track">
          {[...TICKER, ...TICKER, ...TICKER].map((t, i) => (
            <span key={i}>{t} ✦</span>
          ))}
        </div>
      </div>

      <Reveal className="cats">
        <div className="section-head">
          <h2>Shop by style</h2>
          <Link to="/products">See all →</Link>
        </div>
        <div className="cat-grid">
          {CATEGORIES.map((c, i) => {
            const cover = byId(c.cover)
            return (
              <Link key={c.key} to={`/products?type=${c.key}`} className="cat" style={{ animationDelay: `${i * 70}ms` }}>
                {cover && <img src={cover.image_url} alt="" width={200} height={200} loading="lazy" />}
                <span className="cat-label">{c.label}</span>
                <span className="cat-blurb">{c.blurb}</span>
              </Link>
            )
          })}
        </div>
      </Reveal>

      {top.length > 0 && (
        <Reveal>
          <div className="section-head">
            <h2>Top picks</h2>
            <span className="muted small">Hover a card for a sneak peek</span>
          </div>
          <div className="grid">
            {top.map((p) => (
              <PeekCard key={p.product_id} product={p} />
            ))}
          </div>
        </Reveal>
      )}

      <Reveal className="quotes">
        {QUOTES.map((q) => (
          <blockquote key={q}>“{q}”</blockquote>
        ))}
      </Reveal>

      <Reveal>
        <RecommendedForYou limit={4} />
      </Reveal>
    </>
  )
}
