import { useCallback, useEffect, useState } from 'react'
import { fetchProductsCached, fetchRecommendations, type Recommendations } from '../api'
import { useAuth } from '../auth-context'
import ProductCard from './ProductCard'
import StylistThinking from './StylistThinking'

const MIN_THINKING_MS = 1800 // long enough to read as "the stylist is choosing", short enough not to annoy

/**
 * Personal picks from GET /api/recommendations (Problem 9), based on the
 * shopper's closet, wish list and chat history. Guests see staff picks.
 * Problem 10: the stylist "thinks" first, then picks deal in one by one, and
 * "Restyle me" runs it again. `refreshKey` reloads after closet/wish-list changes.
 */
export default function RecommendedForYou({ limit = 8, refreshKey = 0 }: { limit?: number; refreshKey?: number }) {
  const { user } = useAuth()
  const [recs, setRecs] = useState<Recommendations | null>(null)
  const [thinking, setThinking] = useState(true)
  const [rackImages, setRackImages] = useState<string[]>([])
  const [runs, setRuns] = useState(0)

  useEffect(() => {
    fetchProductsCached()
      .then((all) => setRackImages(all.filter((_, i) => i % 9 === 0).map((p) => p.image_url)))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    let cancelled = false
    setThinking(true)
    const started = Date.now()
    fetchRecommendations(limit)
      .catch(() => null)
      .then((r) => {
        const wait = Math.max(0, MIN_THINKING_MS - (Date.now() - started))
        window.setTimeout(() => {
          if (cancelled) return
          setRecs(r)
          setThinking(false)
        }, wait)
      })
    return () => {
      cancelled = true
    }
  }, [user?.id, limit, refreshKey, runs])

  const restyle = useCallback(() => setRuns((n) => n + 1), [])

  const b = recs?.based_on ?? {}
  const basis = [
    b.closet && `${b.closet} closet item${b.closet === 1 ? '' : 's'}`,
    b.wishlist && `${b.wishlist} wish-list item${b.wishlist === 1 ? '' : 's'}`,
    b.chat && `${b.chat} product${b.chat === 1 ? '' : 's'} from your chats`,
  ].filter(Boolean)

  return (
    <section className="recs">
      <div className="section-head">
        <div>
          <h2>{recs && !recs.personalized ? 'Staff picks' : `Recommended for you${user ? `, ${user.first_name}` : ''}`}</h2>
          {!thinking && recs && (
            <span className="muted small">
              {recs.personalized ? `Based on ${basis.join(', ')}` : user ? 'Add items to your closet or wish list for personal picks' : 'Log in for personal picks'}
            </span>
          )}
        </div>
        {!thinking && recs && recs.items.length > 0 && (
          <button className="btn-small restyle" onClick={restyle}>
            ✨ Restyle me
          </button>
        )}
      </div>
      {thinking ? (
        <StylistThinking images={rackImages} />
      ) : recs && recs.items.length > 0 ? (
        <div className="grid deal">
          {recs.items.map((r, i) => (
            <div key={r.product.product_id} className="deal-in" style={{ animationDelay: `${i * 90}ms` }}>
              <ProductCard product={r.product} note={recs.personalized ? `✨ ${r.reason}` : undefined} />
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
