// Types and calls for the FastAPI backend (backend/main.py).

export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string // compressed 360 px WebP for cards (Problem 9)
  image_url_large: string // compressed 800 px WebP for the product page
  image_url_original: string
  price: number
  inventory: SizeStock[]
  total_stock: number
}

/** What any product card needs. Product (Products page) and ChatProduct (from the chat) both fit. */
export type CardProduct = Pick<Product, 'product_id' | 'name' | 'garment_type' | 'description' | 'price' | 'image_url' | 'total_stock'>

/** A product card sent by the chat (backend/models.py ProductCard). */
export interface ChatProduct extends CardProduct {
  colors: string[]
  sizes_in_stock: string[]
}

/** A chat search to render on the page (backend/models.py PageResults). */
export interface PageResults {
  title: string
  query: string
  filters: Record<string, string | number>
  total_matches: number
  products: ChatProduct[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: ChatProduct[]
  page?: PageResults
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (productId: string) =>
  getJson<Product>(`/api/products/${encodeURIComponent(productId)}`)

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

// ---- Auth (backend/auth.py). The session lives in an HttpOnly cookie, so the
// browser sends it automatically and page code never sees it.

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

export interface SignupForm {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    // FastAPI sends {detail: "message"}, or a list of field errors for bad input.
    const detail = data?.detail
    throw new Error(typeof detail === 'string' ? detail : 'Please check the form and try again.')
  }
  return data as T
}

export const signup = (form: SignupForm) => postJson<User>('/api/auth/signup', form)

export const login = (email: string, password: string) => postJson<User>('/api/auth/login', { email, password })

export const logout = () => postJson<{ ok: boolean }>('/api/auth/logout')

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  return res.ok ? ((await res.json()) as User) : null
}

/**
 * Send the shopper's message to the agent (POST /api/chat in backend/main.py).
 * Earlier turns go along so the agent remembers the conversation, including
 * which product cards it showed.
 */
export async function sendChatMessage(message: string, earlier: ChatMessage[], page: PageContext): Promise<ChatMessage> {
  // Logged-in shoppers' history is read from the database on the server; this
  // copy is only used for guests.
  const history = earlier.map((m) => ({
    role: m.role,
    content: m.content,
    product_ids: (m.products ?? []).map((p) => p.product_id),
  }))
  const data = await postJson<{ reply: string; products: ChatProduct[]; page_results: PageResults | null }>('/api/chat', {
    message,
    history,
    page,
  })
  return { role: 'assistant', content: data.reply, products: data.products, page: data.page_results ?? undefined }
}

/** Where the shopper is when they send a message (backend/models.py PageContext). Identifiers only. */
export interface PageContext {
  path: string
  product_id: string | null
  showing_chat_results: boolean
}

/** A returning logged-in shopper's saved conversation (GET /api/chat/history). Empty for guests. */
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await fetch('/api/chat/history')
  if (!res.ok) return []
  const data = (await res.json()) as {
    messages: { role: 'user' | 'assistant'; content: string; products: ChatProduct[]; page_results: PageResults | null }[]
  }
  return data.messages.map((m) => ({
    role: m.role,
    content: m.content,
    products: m.products,
    page: m.page_results ?? undefined,
  }))
}

// ---- My Closet, Wish List, recommendations (Problem 9) ------------------------

export type ListKind = 'closet' | 'wishlist'

export interface ListItem {
  id: number
  size: string | null
  added_at: string
  product: ChatProduct
  size_status: 'in stock' | 'sold out' | null
}

export interface Recommendation {
  product: ChatProduct
  reason: string
  score: number
}

export interface Recommendations {
  personalized: boolean
  based_on: Record<string, number>
  items: Recommendation[]
}

async function sendJson<T>(method: 'POST' | 'DELETE', url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
  return data as T
}

export const fetchList = (kind: ListKind) => getJson<ListItem[]>(`/api/me/${kind}`)

export const addToList = (kind: ListKind, product_id: string, size: string | null) =>
  sendJson<ListItem>('POST', `/api/me/${kind}`, { product_id, size })

export const removeFromList = (kind: ListKind, itemId: number) => sendJson<{ ok: boolean }>('DELETE', `/api/me/${kind}/${itemId}`)

export const moveToCloset = (itemId: number) => sendJson<ListItem>('POST', `/api/me/wishlist/${itemId}/move-to-closet`)

export const fetchRecommendations = (limit = 8) => getJson<Recommendations>(`/api/recommendations?limit=${limit}`)

// One shared catalogue request for components that only need to read it (Shop menu, Home, peeks).
let catalogueCache: Promise<Product[]> | null = null
export function fetchProductsCached(): Promise<Product[]> {
  catalogueCache ??= fetchProducts().catch((err) => {
    catalogueCache = null
    throw err
  })
  return catalogueCache
}
