// Underline tabs. tabs: [{ value, label, count? }]
export default function Tabs({ tabs, value, onChange, className = '' }) {
  return (
    <div className={`flex gap-4 border-b border-line ${className}`} role="tablist">
      {tabs.map(({ value: v, label, count }) => {
        const active = v === value
        return (
          <button
            key={v}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(v)}
            className={`-mb-px flex h-9 items-center gap-1.5 border-b-2 text-[13px] font-medium transition-colors duration-150 ${
              active ? 'border-brand text-fg' : 'border-transparent text-fg-muted hover:text-fg'
            }`}
          >
            {label}
            {typeof count === 'number' && (
              <span className={`rounded px-1 text-[11px] font-medium tabular-nums ${active ? 'bg-brand-subtle text-brand' : 'bg-surface-3 text-fg-subtle'}`}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
