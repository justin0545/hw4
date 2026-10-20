import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { SignupForm } from '../api'
import { useAuth } from '../auth-context'

const MIN_PASSWORD_LENGTH = 8 // keep in sync with backend/auth.py
const EMPTY: SignupForm = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function CreateAccount() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupForm>(EMPTY)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  const set = (field: keyof SignupForm) => (e: ChangeEvent<HTMLInputElement>) => setForm({ ...form, [field]: e.target.value })
  const mismatch = form.confirm_password !== '' && form.password !== form.confirm_password

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password.length < MIN_PASSWORD_LENGTH) return setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
    if (form.password !== form.confirm_password) return setError("Passwords don't match.")
    setPending(true)
    try {
      await signup(form)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPending(false)
    }
  }

  if (user)
    return (
      <div className="auth">
        <h1>Create Account</h1>
        <p>
          You're logged in as <strong>{user.email}</strong>. <Link to="/products">Start shopping</Link>
        </p>
      </div>
    )

  return (
    <div className="auth">
      <h1>Create Account</h1>
      <form onSubmit={onSubmit} className="form">
        <div className="form-row">
          <label>
            First name
            <input autoComplete="given-name" value={form.first_name} onChange={set('first_name')} required />
          </label>
          <label>
            Last name
            <input autoComplete="family-name" value={form.last_name} onChange={set('last_name')} required />
          </label>
        </div>
        <label>
          Email
          <input type="email" autoComplete="email" value={form.email} onChange={set('email')} required />
        </label>
        <label>
          Password
          <input type="password" autoComplete="new-password" value={form.password} onChange={set('password')} required />
          <span className="hint">At least {MIN_PASSWORD_LENGTH} characters</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={set('confirm_password')}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className="hint hint-error">Passwords don't match</span>}
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn" disabled={pending}>
          {pending ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  )
}
