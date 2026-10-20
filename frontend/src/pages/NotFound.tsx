import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="prose">
      <h1>Page not found</h1>
      <p>
        That page doesn't exist. <Link to="/">Go back home</Link>.
      </p>
    </div>
  )
}
