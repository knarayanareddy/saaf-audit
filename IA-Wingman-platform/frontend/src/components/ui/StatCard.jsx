import { Card } from './Card'
import { tokenColor } from '../../lib/color'

// A KPI tile with an accent bar, big value, label, and optional context line.
// `accent` is a THEME TOKEN name ('--chart-2', '--sev-high'), not a hex, so the
// tile follows the brand colour and stays legible in dark mode.
export default function StatCard({ value, label, hint, accent = '--brand', icon: Icon, onClick }) {
  const clickable = typeof onClick === 'function'
  return (
    <Card
      as={clickable ? 'button' : 'div'}
      hover={clickable}
      onClick={onClick}
      className={`relative overflow-hidden p-5 text-left ${clickable ? 'w-full' : ''}`}
    >
      <span className="absolute inset-y-0 left-0 w-1" style={{ background: tokenColor(accent) }} />
      <div className="flex items-start justify-between">
        <div>
          <div className="text-3xl font-semibold tabular-nums text-fg">{value}</div>
          <div className="mt-1 text-sm text-fg-muted">{label}</div>
        </div>
        {Icon && (
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg"
            style={{ background: tokenColor(accent, 0.14), color: tokenColor(accent) }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>
      {hint && <div className="mt-3 text-xs font-medium text-fg-subtle">{hint}</div>}
    </Card>
  )
}
