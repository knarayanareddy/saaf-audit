import { ENTITIES, STATUS_META, statusColor, statusInk } from '../../lib/entities'

// The entity badge is deliberately colourless: which business unit an audit
// belongs to is a label, not a signal, and giving each one a hue was the single
// biggest source of colour noise on the dashboard.
export function EntityBadge({ entity }) {
  const meta = ENTITIES[entity]
  return (
    <span className="inline-flex h-5 shrink-0 items-center whitespace-nowrap rounded px-1.5 text-[11px] font-medium text-fg-muted ring-1 ring-inset ring-line">
      {meta?.label || entity}
    </span>
  )
}

// Status keeps its colour — it is the one categorical dimension where the value
// itself matters. Soft fill, same-hue text, one dot: the badge, the donut and the
// timeline all read from the same tokens, so they can never drift apart.
export function StatusBadge({ status }) {
  const meta = STATUS_META[status]
  return (
    <span
      className="inline-flex h-5 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full pl-1.5 pr-2 text-[11px] font-medium"
      style={{
        backgroundColor: statusColor(status, 0.22),
        color: statusInk(status),
        boxShadow: `inset 0 0 0 1px ${statusColor(status, 0.45)}`,
      }}
    >
      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: statusColor(status) }} />
      {meta?.label || status}
    </span>
  )
}

export function Tag({ children, className = '' }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${className}`}>
      {children}
    </span>
  )
}
