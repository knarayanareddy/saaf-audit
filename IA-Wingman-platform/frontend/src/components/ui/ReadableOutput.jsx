import { Check, AlertTriangle, TriangleAlert, Info, Search, Sparkles } from 'lucide-react'

// The readable-output system: turn structured agent JSON into scannable UI so a
// medior auditor is never overwhelmed. Summary first, then bulleted key points
// with consistent severity signs; detail lives in <Collapsible> sections.

// TL;DR block, always visible at the top of an agent output.
export function SummaryCard({ title = 'Summary', children, icon: Icon = Sparkles }) {
  return (
    <div className="rounded-xl border border-brand/20 bg-brand-faint p-4">
      <div className="mb-1.5 flex items-center gap-1.5 text-caption text-brand">
        <Icon size={13} /> {title}
      </div>
      <div className="text-sm text-fg">{children}</div>
    </div>
  )
}

const SIGN = {
  ok: { icon: Check, cls: 'text-sev-low' },
  gap: { icon: AlertTriangle, cls: 'text-sev-med' },
  risk: { icon: TriangleAlert, cls: 'text-sev-high' },
  info: { icon: Info, cls: 'text-fg-subtle' },
  check: { icon: Search, cls: 'text-brand' },
}

// Bulleted list with a consistent leading sign per item.
// items: [{ text, sign?: 'ok'|'gap'|'risk'|'info'|'check', trailing?: node }]
export function KeyPoints({ items = [], sign = 'info' }) {
  return (
    <ul className="space-y-1.5">
      {items.map((it, i) => {
        const s = SIGN[it.sign || sign] || SIGN.info
        const Icon = s.icon
        return (
          <li key={i} className="flex items-start gap-2 text-sm text-fg-muted">
            <Icon size={14} className={`mt-0.5 shrink-0 ${s.cls}`} />
            <span className="min-w-0 flex-1">{it.text}</span>
            {it.trailing}
          </li>
        )
      })}
    </ul>
  )
}
