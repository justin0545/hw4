import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import type { PageResults } from '../api'
import { ChatResultsContext } from '../chat-results-context'

export default function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(null)
  const navigate = useNavigate()

  // Show the results on the Products page, from wherever the shopper is chatting.
  const showResults = useCallback(
    (r: PageResults) => {
      setResults(r)
      navigate('/products')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [navigate],
  )
  const clearResults = useCallback(() => setResults(null), [])

  const value = useMemo(() => ({ results, showResults, clearResults }), [results, showResults, clearResults])
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}
