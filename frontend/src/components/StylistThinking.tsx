import { useEffect, useState } from 'react'
import Bulldog from './Bulldog'

const STEPS = ['Peeking in your closet…', 'Matching colors and layers…', 'Flipping through the racks…', 'Picking pieces for you…']

/**
 * The "stylist is thinking" animation shown while recommendations load
 * (Problem 10): the bulldog stylist with a spinning cogwheel, flipping through
 * a clothes rack whose hangers cycle through real product photos.
 */
export default function StylistThinking({ images }: { images: string[] }) {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const t = window.setInterval(() => setStep((s) => (s + 1) % STEPS.length), 700)
    return () => window.clearInterval(t)
  }, [])

  const rack = images.length ? images : []
  return (
    <div className="thinking" role="status" aria-live="polite">
      <div className="thinking-stylist">
        <svg className="cog" viewBox="0 0 48 48" aria-hidden="true">
          <path
            d="M27.4 4l1.2 5.2a15.6 15.6 0 0 1 4.1 1.7l4.5-2.9 4.8 4.8-2.9 4.5a15.6 15.6 0 0 1 1.7 4.1l5.2 1.2v6.8l-5.2 1.2a15.6 15.6 0 0 1-1.7 4.1l2.9 4.5-4.8 4.8-4.5-2.9a15.6 15.6 0 0 1-4.1 1.7L27.4 44h-6.8l-1.2-5.2a15.6 15.6 0 0 1-4.1-1.7l-4.5 2.9-4.8-4.8 2.9-4.5a15.6 15.6 0 0 1-1.7-4.1L2 27.4v-6.8l5.2-1.2a15.6 15.6 0 0 1 1.7-4.1L6 10.8 10.8 6l4.5 2.9a15.6 15.6 0 0 1 4.1-1.7L20.6 4zM24 17a7 7 0 1 0 0 14 7 7 0 0 0 0-14z"
            fill="currentColor"
          />
        </svg>
        <Bulldog size={84} className="bob" />
      </div>
      <div className="rack" aria-hidden="true">
        <div className="rack-bar" />
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="hanger" style={{ animationDelay: `${i * 0.18}s` }}>
            <span className="hook" />
            <div className="garment">
              {rack.length > 0 && <img src={rack[(i + step) % rack.length]} alt="" width={64} height={64} />}
            </div>
          </div>
        ))}
      </div>
      <p className="thinking-text">
        <strong>Your stylist is thinking</strong>
        <span key={step}>{STEPS[step]}</span>
      </p>
    </div>
  )
}
