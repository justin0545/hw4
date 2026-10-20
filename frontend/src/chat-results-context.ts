import { createContext, useContext } from 'react'
import type { PageResults } from './api'

/**
 * Chat search results shown on the page (Problem 7). The chat widget sets them
 * when the agent sends page_results; the Products page renders them. Kept in
 * memory, so they survive clicking into a product and coming back.
 */
export interface ChatResultsState {
  results: PageResults | null
  showResults: (results: PageResults) => void
  clearResults: () => void
}

export const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
