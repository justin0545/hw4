import { Link } from 'react-router-dom'

export default function LoginPrompt({ what }: { what: string }) {
  return (
    <div className="empty">
      <p>
        <Link to="/login">Log in</Link> or <Link to="/create-account">create an account</Link> to use {what}.
      </p>
    </div>
  )
}
