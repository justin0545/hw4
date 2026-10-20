import { Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar'
import ChatWidget from './components/ChatWidget'
import BagDrawer from './components/BagDrawer'
import Bulldog from './components/Bulldog'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'
import NotFound from './pages/NotFound'
import Closet from './pages/Closet'
import Wishlist from './pages/Wishlist'

export default function App() {
  return (
    <>
      <NavBar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="/closet" element={<Closet />} />
          <Route path="/wishlist" element={<Wishlist />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="footer">
        <Bulldog size={44} />
        <div>
          <strong className="footer-brand">Campus Customs</strong>
          <span>Yale spirit apparel · New Haven, CT · © 2026</span>
        </div>
      </footer>
      <BagDrawer />
      <ChatWidget />
    </>
  )
}
