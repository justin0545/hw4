import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProductsCached, type Product } from '../api'
import { useChatResults } from '../chat-results-context'
import PeekCard from '../components/PeekCard'
import ProductCard from '../components/ProductCard'
import { CATEGORIES, TOP_PICKS, family } from '../shop'

export default function Products() {
  const { results, clearResults } = useChatResults()
  const [params] = useSearchParams()
  const type = params.get('type')
  // Picking a category (nav Shop menu, Home tiles) replaces any chat results on the page.
  useEffect(() => {
    if (type) clearResults()
  }, [type, clearResults])
  return results && !type ? <ChatResults /> : <Catalogue />
}

/** Products the chat assistant found (Problem 7). Same cards, same detail links as the catalogue. */
function ChatResults() {
  const { results, clearResults } = useChatResults()
  if (!results) return null
  const shown = results.products.length
  const filters = Object.entries(results.filters)
    .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${k.includes('price') ? `$${v}` : v}`)
    .join(' · ')

  return (
    <>
      <div className="chat-results-banner" role="status">
        <div>
          <div className="chat-results-kicker">💬 From your chat with our assistant</div>
          <h1>{results.title}</h1>
          <p className="muted">
            {shown < results.total_matches ? `Showing the top ${shown} of ${results.total_matches} matches` : `${shown} ${shown === 1 ? 'match' : 'matches'}`}
            {results.query && <> for “{results.query}”</>}
            {filters && <> · {filters}</>}
          </p>
        </div>
        <button className="btn btn-ghost" onClick={clearResults}>
          Show all products
        </button>
      </div>
      <div className="grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </>
  )
}

function Catalogue() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [params, setParams] = useSearchParams()
  const fam = params.get('type') ?? ''
  const category = CATEGORIES.find((c) => c.key === fam)

  useEffect(() => {
    fetchProductsCached()
      .then(setProducts)
      .catch(() => setError("We couldn't load products. Is the backend running on port 8000?"))
  }, [])

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (products ?? []).filter(
      (p) =>
        (!fam || family(p.garment_type) === fam) &&
        (!q || [p.name, p.description, p.garment_type, ...p.colors, ...p.search_tags].join(' ').toLowerCase().includes(q)),
    )
  }, [products, query, fam])

  return (
    <>
      <div className="page-head">
        <div>
          <p className="page-kicker">The Campus Customs collection</p>
          <h1>{category ? category.label : 'All spirit gear'}</h1>
        </div>
        {products && (
          <span className="muted">
            {shown.length} of {products.length} items
          </span>
        )}
      </div>

      <div className="pills" role="tablist" aria-label="Category">
        <button role="tab" aria-selected={!fam} className={!fam ? 'on' : ''} onClick={() => setParams({})}>
          All
        </button>
        {CATEGORIES.map((c) => (
          <button key={c.key} role="tab" aria-selected={fam === c.key} className={fam === c.key ? 'on' : ''} onClick={() => setParams({ type: c.key })}>
            {c.label}
          </button>
        ))}
      </div>

      <div className="filters">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search hoodies, bulldog, navy, Branford…" aria-label="Search products" />
      </div>

      {error && <p className="error">{error}</p>}
      {!products && !error && <p className="muted">Loading products…</p>}
      {products && shown.length === 0 && <p className="muted">No products match your search.</p>}

      <div className="grid">
        {shown.map((p) =>
          TOP_PICKS.includes(p.product_id) ? <PeekCard key={p.product_id} product={p} /> : <ProductCard key={p.product_id} product={p} />,
        )}
      </div>
    </>
  )
}
