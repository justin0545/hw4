import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchList, removeFromList, type ListItem } from '../api'
import { useAuth } from '../auth-context'
import LoginPrompt from '../components/LoginPrompt'
import ProductCard from '../components/ProductCard'
import RecommendedForYou from '../components/RecommendedForYou'

const added = (iso: string) => new Date(iso.replace(' ', 'T') + 'Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

/** My Closet (Problem 9): what the shopper already owns, plus picks that go with it. */
export default function Closet() {
  const { user, loading } = useAuth()
  const [items, setItems] = useState<ListItem[] | null>(null)
  const [version, setVersion] = useState(0)

  const load = useCallback(() => {
    fetchList('closet')
      .then(setItems)
      .catch(() => setItems([]))
  }, [])

  useEffect(() => {
    if (user) load()
  }, [user, load])

  async function remove(id: number) {
    await removeFromList('closet', id)
    load()
    setVersion((v) => v + 1)
  }

  if (loading) return null
  if (!user)
    return (
      <>
        <h1>My Closet</h1>
        <LoginPrompt what="My Closet" />
      </>
    )

  return (
    <>
      <div className="section-head">
        <h1>My Closet</h1>
        {items && <span className="muted">{items.length} {items.length === 1 ? 'item' : 'items'}</span>}
      </div>
      <p className="muted lead-in">
        The Campus Customs gear you already own. We use it to recommend pieces that go with what you have and to skip things you
        already bought.
      </p>
      {items && items.length === 0 && (
        <div className="empty">
          <p>
            Your closet is empty. Open any product and click <strong>“I own this”</strong>, or move items here from your{' '}
            <Link to="/wishlist">wish list</Link> after you buy them.
          </p>
        </div>
      )}
      <div className="grid">
        {items?.map((i) => (
          <ProductCard
            key={i.id}
            product={i.product}
            note={`${i.size ? `Size ${i.size} · ` : ''}Added ${added(i.added_at)}`}
            actions={
              <button className="btn-small" onClick={() => remove(i.id)}>
                Remove
              </button>
            }
          />
        ))}
      </div>
      <RecommendedForYou refreshKey={version + (items?.length ?? 0)} />
    </>
  )
}
