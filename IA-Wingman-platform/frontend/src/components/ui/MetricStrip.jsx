import { tokenColor } from '../../lib/color'

// KPIs as one continuous strip instead of four floating tiles. The numbers are
// the content; the hairlines between them are the only structure needed. Reading
// four values in a row is faster than reading four cards, which is the point.
//
// items: [{ key, value, label, hint?, accent?, onClick? }]
//   accent — a theme token name ('--chart-2', '--sev-high'); drawn as a small
//   marker beside the number, never as a filled block.
export default function MetricStrip({ items = [], className = '' }) {
  return (
    <div className={`grid grid-cols-2 divide-x divide-line-subtle overflow-hidden rounded-lg border border-line bg-surface sm:grid-cols-4 ${className}`}>
      {items.map(({ key, value, label, hint, accent, onClick }) => {
        const Tag = onClick ? 'button' : 'div'
        return (
          <Tag
            key={key}
            onClick={onClick}
            className={`min-w-0 px-4 py-3 text-left transition-colors duration-150 ${
              onClick ? 'hover:bg-surface-2' : ''
            }`}
          >
            <div className="flex items-center gap-1.5">
              {accent && (
                <span className="h-2.5 w-0.5 shrink-0 rounded-full" style={{ background: tokenColor(accent) }} />
              )}
              <span className="text-caption truncate">{label}</span>
            </div>
            <div className="mt-1 text-metric text-fg">{value}</div>
            {hint && <div className="text-meta mt-0.5 truncate">{hint}</div>}
          </Tag>
        )
      })}
    </div>
  )
}
