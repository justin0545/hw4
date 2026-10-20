import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="prose">
      <h1>About Us</h1>
      <p className="lead">
        We are Campus Customs, the premier location for Yale University apparel and gear. We offer some of the best options
        on campus for showing off your university pride. Stop by and take a look and bring your spirit game to the next
        level!
      </p>

      <h2>What we carry</h2>
      <p>
        Our shelves cover everything you need for game day, class, or a cold New Haven morning: hoodies and crewneck
        sweatshirts, T-shirts, quarter-zips, fleece and jackets. You'll find classic YALE wordmarks, vintage bulldog
        graphics, residential college designs, and left-chest marks for Yale's varsity teams.
      </p>

      <h2>Who we serve</h2>
      <p>
        Students, alumni, parents, faculty, staff and fans. Whether you're heading to The Game or sending a care package,
        we'll help you find the right piece in the right size.
      </p>

      <h2>Need help choosing?</h2>
      <p>
        Use the chat button in the bottom-right corner to ask about products, colors and sizes, or <Link to="/products">browse
        the full catalogue</Link>.
      </p>
    </div>
  )
}
