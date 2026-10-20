import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { CartContext, type BagItem } from '../cart-context'

const STORAGE_KEY = 'campus-customs-bag'

function loadBag(): BagItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as BagItem[]) : []
  } catch {
    return []
  }
}

/** Shopping bag kept in localStorage so it survives page reloads (a per-browser convenience). */
export default function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<BagItem[]>(loadBag)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
    } catch {
      /* private window or storage blocked: the bag still works for this visit */
    }
  }, [items])

  const add = useCallback((item: Omit<BagItem, 'key' | 'qty'>) => {
    const key = `${item.product_id}|${item.size}`
    setItems((cur) =>
      cur.some((i) => i.key === key) ? cur.map((i) => (i.key === key ? { ...i, qty: Math.min(i.qty + 1, 10) } : i)) : [...cur, { ...item, key, qty: 1 }],
    )
  }, [])
  const setQty = useCallback((key: string, qty: number) => {
    setItems((cur) => (qty <= 0 ? cur.filter((i) => i.key !== key) : cur.map((i) => (i.key === key ? { ...i, qty: Math.min(qty, 10) } : i))))
  }, [])
  const remove = useCallback((key: string) => setItems((cur) => cur.filter((i) => i.key !== key)), [])
  const clear = useCallback(() => setItems([]), [])

  const value = useMemo(
    () => ({
      items,
      count: items.reduce((n, i) => n + i.qty, 0),
      total: items.reduce((t, i) => t + i.qty * i.price, 0),
      open,
      setOpen,
      add,
      setQty,
      remove,
      clear,
    }),
    [items, open, add, setQty, remove, clear],
  )
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
