import { Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'

// One back-link style app-wide (replaces three ad-hoc variants).
export function BackLink({ to, label = 'Back' }) {
  return (
    <Link
      to={to}
      className="mb-3 inline-flex items-center gap-1 text-[13px] text-fg-muted transition-colors duration-150 hover:text-fg"
    >
      <ChevronLeft size={15} />
      {label}
    </Link>
  )
}

// One page header: optional back-link, badge row, title, subtitle, right-aligned
// actions. Keeps every page's masthead identical.
export function PageHeader({ back, badges, title, subtitle, actions }) {
  return (
    <div className="mb-5">
      {back && <BackLink to={back.to} label={back.label} />}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          {badges && <div className="mb-1.5 flex flex-wrap items-center gap-1.5">{badges}</div>}
          <h1 className="text-h1 text-fg">{title}</h1>
          {subtitle && <div className="mt-1 text-[13px] text-fg-muted">{subtitle}</div>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}
