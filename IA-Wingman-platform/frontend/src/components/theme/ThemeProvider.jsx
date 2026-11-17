import { useEffect } from 'react'
import { useStore } from '../../store/useStore'

// Applies the selected theme to <html data-theme>. 'system' follows the OS and
// updates live when the OS preference changes. Kept side-effect-only so there is
// no flash: the initial value is read synchronously in index.html's inline script.
export default function ThemeProvider({ children }) {
  const theme = useStore((s) => s.theme)

  useEffect(() => {
    const root = document.documentElement
    const mq = window.matchMedia('(prefers-color-scheme: dark)')

    const apply = () => {
      const resolved = theme === 'system' ? (mq.matches ? 'dark' : 'light') : theme
      root.setAttribute('data-theme', resolved)
    }
    apply()

    if (theme === 'system') {
      mq.addEventListener('change', apply)
      return () => mq.removeEventListener('change', apply)
    }
  }, [theme])

  return children
}
