import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.jsx'
import ThemeProvider from './components/theme/ThemeProvider'
import BrandProvider from './components/theme/BrandProvider'
import './index.css'
import { reloadForNewVersion } from './lib/staleBuild'

// Vite's own signal that a chunk or its preload could not be fetched — the
// usual sign of a tab opened before the latest deploy (lib/staleBuild.js).
window.addEventListener('vite:preloadError', (event) => {
  if (reloadForNewVersion()) event.preventDefault()
})

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrandProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </BrandProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
