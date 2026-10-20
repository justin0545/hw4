import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend (backend/main.py) runs on port 8000. Proxying keeps the
// frontend code using relative URLs like /api/products and /media/products/...
const backend = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/media': backend,
    },
  },
})
