import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, matchPath, useLocation } from 'react-router-dom'
import { fetchChatHistory, formatPrice, sendChatMessage, type ChatMessage, type PageContext } from '../api'
import { useAuth } from '../auth-context'
import { useChatResults } from '../chat-results-context'
import Bulldog from './Bulldog'

// `local` messages (greeting, notes, errors) are shown but never sent to the agent.
type WidgetMessage = ChatMessage & { local?: boolean; note?: boolean }

const greeting = (name?: string, returning = false): WidgetMessage => ({
  role: 'assistant',
  content: returning
    ? `Welcome back, ${name}! 🐾 Your earlier conversation is above. Want to pick up where we left off, or style something new?`
    : `Hey${name ? ` ${name}` : ' there'}! 🐾 I'm your Campus Customs Stylist. Tell me where you're headed (game day, class, a gift?) and I'll put together the perfect Yale look.`,
  local: true,
})

const note = (content: string): WidgetMessage => ({ role: 'assistant', content, local: true, note: true })

/** Quick starts shown until the shopper sends a first message (Problem 10). */
const STARTERS = ['🏈 Outfit for game day at the Bowl', '🎁 Gift for a parent', '☕ Cozy hoodie for class', '✨ What goes with what I own?']

export default function ChatWidget() {
  const { user } = useAuth()
  const { results, showResults } = useChatResults()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<WidgetMessage[]>([greeting()])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [hint, setHint] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Shopper changes (page load, log in, log out): logged-in shoppers get their
  // saved conversation back from the database; guests start fresh.
  useEffect(() => {
    let cancelled = false
    if (!user) {
      setMessages([greeting()])
      return
    }
    setMessages([greeting(user.first_name)])
    fetchChatHistory().then((saved) => {
      if (cancelled || saved.length === 0) return
      setMessages([note('Saved conversation'), ...saved, greeting(user.first_name, true)])
    })
    return () => {
      cancelled = true
    }
  }, [user])

  /** Where the shopper is right now, sent with every message so "this" can be resolved. */
  function pageContext(): PageContext {
    const match = matchPath('/products/:productId', location.pathname)
    return {
      path: location.pathname,
      product_id: match?.params.productId ?? null,
      showing_chat_results: location.pathname === '/products' && results !== null,
    }
  }

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // A friendly "Ask the Stylist" bubble a few seconds after arriving, once per visit.
  useEffect(() => {
    const show = window.setTimeout(() => setHint(true), 2500)
    const hide = window.setTimeout(() => setHint(false), 9500)
    return () => {
      window.clearTimeout(show)
      window.clearTimeout(hide)
    }
  }, [])

  async function send(text: string) {
    text = text.trim()
    if (!text || sending) return
    const earlier = messages.filter((m) => !m.local)
    setMessages((m) => [...m, { role: 'user', content: text }])
    setDraft('')
    setSending(true)
    try {
      const reply = await sendChatMessage(text, earlier, pageContext())
      setMessages((m) => [...m, reply])
      if (reply.page) showResults(reply.page) // the agent's search fills the Products page
    } catch (err) {
      const content = (err as Error).message || 'Sorry, something went wrong. Please try again.'
      setMessages((m) => [...m, { role: 'assistant', content, local: true }])
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  // Other parts of the site can open the chat, optionally with a question (shop.ts openStylist).
  const sendRef = useRef(send)
  sendRef.current = send
  useEffect(() => {
    const onOpen = (e: Event) => {
      setOpen(true)
      setHint(false)
      const message = (e as CustomEvent<{ message?: string }>).detail?.message
      if (message) window.setTimeout(() => sendRef.current(message), 150)
    }
    window.addEventListener('open-stylist', onOpen)
    return () => window.removeEventListener('open-stylist', onOpen)
  }, [])

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    send(draft)
  }

  // Starter chips until the shopper says something this visit (also for returning shoppers).
  const last = messages[messages.length - 1]
  const fresh = !!last && last.local === true && !last.note && last.role === 'assistant' && !last.content.startsWith('Sorry')

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Chat with the Campus Customs Stylist">
          <header className="chat-head">
            <div className="chat-avatar">
              <Bulldog size={40} />
            </div>
            <div className="chat-title">
              <strong>Campus Customs Stylist</strong>
              <span>
                <i className="online-dot" /> Online · outfits, sizes &amp; stock
              </span>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>
          <div className="chat-list" ref={listRef}>
            {messages.map((m, i) =>
              m.note ? (
                <div key={i} className="chat-note">
                  {m.content}
                </div>
              ) : (
                <div key={i} className={`chat-turn ${m.role}`}>
                  {m.role === 'assistant' && (
                    <div className="mini-avatar" aria-hidden="true">
                      <Bulldog size={26} />
                    </div>
                  )}
                  <div className="chat-stack">
                    <div className={`chat-msg ${m.role}`}>{m.content}</div>
                    {m.page && (
                      <button
                        className={`chat-page-link${results === m.page ? ' on' : ''}`}
                        onClick={() => m.page && showResults(m.page)}
                        title="Show these results on the page"
                      >
                        {results === m.page ? '✓ ' : '↗ '}
                        {m.page.total_matches} {m.page.title.toLowerCase()} on the page
                      </button>
                    )}
                    {m.products && m.products.length > 0 && (
                      <div className="chat-cards">
                        {m.products.map((p) => (
                          <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-card">
                            <img src={p.image_url} alt="" width={52} height={52} />
                            <div>
                              <div className="chat-card-name">{p.name}</div>
                              <div className="chat-card-meta">
                                {formatPrice(p.price)} ·{' '}
                                {p.sizes_in_stock.length ? p.sizes_in_stock.join(' ') : <span className="out">Sold out</span>}
                              </div>
                            </div>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ),
            )}
            {fresh && !sending && (
              <div className="chat-chips">
                {STARTERS.map((s) => (
                  <button key={s} onClick={() => send(s.replace(/^\S+\s/, ''))}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {sending && (
              <div className="chat-turn assistant">
                <div className="mini-avatar" aria-hidden="true">
                  <Bulldog size={26} />
                </div>
                <div className="chat-msg assistant typing" aria-label="The stylist is typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              </div>
            )}
          </div>
          <form className="chat-form" onSubmit={onSubmit}>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about a look, a size, a gift…"
              aria-label="Message"
              maxLength={2000}
            />
            <button type="submit" disabled={!draft.trim() || sending} aria-label="Send">
              ➤
            </button>
          </form>
        </section>
      )}
      {hint && !open && (
        <button className="chat-hint" onClick={() => { setOpen(true); setHint(false) }}>
          Need a game-day look? Ask the Stylist! 🐾
        </button>
      )}
      <button className={`chat-toggle${open ? ' is-open' : ''}`} onClick={() => { setOpen((o) => !o); setHint(false) }} aria-label={open ? 'Close chat' : 'Chat with the Stylist'}>
        {open ? <span className="x">×</span> : <Bulldog size={44} mood="wink" />}
      </button>
    </div>
  )
}
