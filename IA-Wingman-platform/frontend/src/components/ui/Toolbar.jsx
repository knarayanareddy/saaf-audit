import { X } from 'lucide-react'

// A single 36px control row: search on the left, filters beside it, a count on
// the right. Replaces stacked rows of filter pills — twenty pills advertise
// twenty choices, a dropdown answers the one question "which entity?".
export default function Toolbar({ children, trailing, className = '' }) {
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {children}
      {trailing && <div className="ml-auto flex items-center gap-2">{trailing}</div>}
    </div>
  )
}

// An applied filter, shown only when it is actually narrowing the list — so the
// bar stays quiet until you use it, and always shows exactly what is active.
export function FilterChip({ label, value, onClear }) {
  return (
    <span className="inline-flex h-7 items-center gap-1 rounded-md border border-line bg-surface-2 pl-2 pr-1 text-xs text-fg-muted">
      <span className="text-fg-subtle">{label}</span>
      <span className="font-medium text-fg">{value}</span>
      <button
        onClick={onClear}
        aria-label={`Clear ${label} filter`}
        className="rounded p-0.5 text-fg-subtle transition-colors duration-150 hover:bg-surface-3 hover:text-fg"
      >
        <X size={12} />
      </button>
    </span>
  )
}
