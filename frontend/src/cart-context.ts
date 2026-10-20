import { createContext, useContext } from 'react'

/** One line in the shopping bag (Problem 10). Kept in this browser only. */
export interface BagItem {
  key: string // `${product_id}|${size}`
  product_id: string
  name: string
  price: number
  image_url: string
  size: string
  qty: number
}

export interface CartState {
  items: BagItem[]
  count: number
  total: number
  open: boolean
  setOpen: (open: boolean) => void
  add: (item: Omit<BagItem, 'key' | 'qty'>) => void
  setQty: (key: string, qty: number) => void
  remove: (key: string) => void
  clear: () => void
}

export const CartContext = createContext<CartState | null>(null)

export function useCart(): CartState {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>')
  return ctx
}
