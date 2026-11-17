import { useEffect } from 'react'
import { useOrg } from '../../lib/useOrg'
import { brandTokens } from '../../lib/color'

// Injects the organization's brand colour into the CSS token system for both
// themes, so IA Wingman re-skins to any org's brand from a single hex.
export default function BrandProvider({ children }) {
  const org = useOrg()
  const hex = org?.brand_hex

  useEffect(() => {
    if (!hex) return
    const { light, dark } = brandTokens(hex)
    const toRules = (sel, vars) =>
      `${sel}{${Object.entries(vars).map(([k, v]) => `${k}:${v}`).join(';')}}`
    const css = toRules(':root', light) + toRules(':root[data-theme="dark"]', dark)

    let el = document.getElementById('brand-vars')
    if (!el) {
      el = document.createElement('style')
      el.id = 'brand-vars'
      document.head.appendChild(el)
    }
    el.textContent = css
  }, [hex])

  return children
}
