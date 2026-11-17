import { useState } from 'react'
import { ChevronRight } from 'lucide-react'

// Expand/collapse section — the backbone of readable agent output (progressive
// disclosure so a medior auditor sees the gist first, detail on demand).
export default function Collapsible({
  title,
  subtitle,
  icon: Icon,
  count,
  badge,
  defaultOpen = false,
  children,
  className = '',
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={`overflow-hidden rounded-xl border border-line bg-surface ${className}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-surface-3"
      >
        <ChevronRight size={16} className={`shrink-0 text-fg-subtle transition-transform ${open ? 'rotate-90' : ''}`} />
        {Icon && <Icon size={16} className="shrink-0 text-brand" />}
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-fg">{title}</span>
            {typeof count === 'number' && (
              <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-semibold text-fg-muted">{count}</span>
            )}
            {badge}
          </span>
          {subtitle && <span className="mt-0.5 block truncate text-xs text-fg-muted">{subtitle}</span>}
        </span>
      </button>
      {open && <div className="border-t border-line px-4 py-3">{children}</div>}
    </div>
  )
}
