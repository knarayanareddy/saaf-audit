import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `vite preview` does not inherit server.proxy, so the built demo build needs
// its own copy — shared here so dev and demo can never drift apart.
const proxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
  '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
}

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
})
