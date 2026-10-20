/**
 * The Campus Customs bulldog mascot: original artwork drawn for this site (not
 * an official Yale mark). Used in the logo, hero, chat avatar and the stylist
 * "thinking" animation. `mood="wink"` closes one eye.
 */
export default function Bulldog({ size = 64, mood = 'happy', className = '' }: { size?: number; mood?: 'happy' | 'wink'; className?: string }) {
  return (
    <svg className={`bulldog ${className}`} width={size} height={size} viewBox="0 0 120 120" aria-hidden="true">
      {/* folded "rose" ears */}
      <path d="M30 34C14 30 6 18 14 12c7-5 20 2 28 12-4 4-8 7-12 10z" fill="var(--yale, #00356b)" />
      <path d="M90 34c16-4 24-16 16-22-7-5-20 2-28 12 4 4 8 7 12 10z" fill="var(--yale, #00356b)" />
      {/* head */}
      <ellipse cx="60" cy="62" rx="44" ry="40" fill="#fff" stroke="var(--yale, #00356b)" strokeWidth="5" />
      {/* brow wrinkles */}
      <path d="M44 36q16-7 32 0M48 30q12-5 24 0" stroke="var(--yale, #00356b)" strokeWidth="3" fill="none" strokeLinecap="round" opacity=".55" />
      {/* eyes */}
      <circle cx="42" cy="54" r="7" fill="var(--yale, #00356b)" />
      <circle cx="44.5" cy="51.5" r="2.2" fill="#fff" />
      {mood === 'wink' ? (
        <path d="M70 55q8-6 16 0" stroke="var(--yale, #00356b)" strokeWidth="4" fill="none" strokeLinecap="round" />
      ) : (
        <>
          <circle cx="78" cy="54" r="7" fill="var(--yale, #00356b)" />
          <circle cx="80.5" cy="51.5" r="2.2" fill="#fff" />
        </>
      )}
      {/* muzzle */}
      <ellipse cx="60" cy="80" rx="27" ry="19" fill="#e8f0fb" stroke="var(--yale, #00356b)" strokeWidth="4" />
      {/* nose */}
      <path d="M49 69q11-7 22 0q-4 9-11 9t-11-9z" fill="var(--yale, #00356b)" />
      {/* mouth + underbite teeth */}
      <path d="M44 88q16 11 32 0" stroke="var(--yale, #00356b)" strokeWidth="4" fill="none" strokeLinecap="round" />
      <path d="M48 89l3.5-7 3.5 7zM65 89l3.5-7 3.5 7z" fill="#fff" stroke="var(--yale, #00356b)" strokeWidth="2" strokeLinejoin="round" />
      {/* spirit collar + tag */}
      <path d="M22 98q38 22 76 0" stroke="var(--sky, #4a9bff)" strokeWidth="8" fill="none" strokeLinecap="round" />
      <circle cx="60" cy="110" r="6.5" fill="var(--gold, #ffc72c)" stroke="var(--yale, #00356b)" strokeWidth="2" />
    </svg>
  )
}
