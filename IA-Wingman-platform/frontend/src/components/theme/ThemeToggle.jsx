import { Sun, Moon, Monitor } from 'lucide-react'
import { useStore } from '../../store/useStore'

const OPTIONS = [
  { value: 'light', icon: Sun, label: 'Light', hint: 'Light — always the light theme, regardless of your device setting' },
  { value: 'system', icon: Monitor, label: 'System', hint: 'System — follow your device (OS) setting; switches automatically when your device does' },
  { value: 'dark', icon: Moon, label: 'Dark', hint: 'Dark — always the dark theme, regardless of your device setting' },
]

// Compact 3-way segmented control. `tone="onBrand"` styles it for the dark
// green sidebar; default styles it for light surfaces.
export default function ThemeToggle({ tone = 'default' }) {
  const theme = useStore((s) => s.theme)
  const setTheme = useStore((s) => s.setTheme)

  const onBrand = tone === 'onBrand'
  const track = onBrand ? 'bg-white/10' : 'bg-surface-3'

  return (
    <div className={`inline-flex items-center gap-0.5 rounded-md p-0.5 ${track}`} role="radiogroup" aria-label="Theme">
      {OPTIONS.map(({ value, icon: Icon, label, hint }) => {
        const active = theme === value
        const activeCls = onBrand
          ? 'bg-white/90 text-brand'
          : 'bg-surface text-fg ring-1 ring-inset ring-line'
        const idleCls = onBrand
          ? 'text-white/60 hover:text-white'
          : 'text-fg-subtle hover:text-fg'
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={hint}
            onClick={() => setTheme(value)}
            className={`flex h-[26px] w-[26px] items-center justify-center rounded transition-colors duration-150 ${active ? activeCls : idleCls}`}
          >
            <Icon size={14} />
          </button>
        )
      })}
    </div>
  )
}
