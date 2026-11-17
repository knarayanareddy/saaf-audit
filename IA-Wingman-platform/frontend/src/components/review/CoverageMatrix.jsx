import { useQuery } from '@tanstack/react-query'
import { Check, AlertTriangle, Circle, ShieldCheck, RefreshCw } from 'lucide-react'
import { getCoverage } from '../../api/review'
import { SummaryCard } from '../ui/ReadableOutput'

// Deterministic assurance sweep over the planning chain — no AI cost. Shows
// which links (risk → scope → questions → tests → frameworks) hold and where
// they break, with consistent ✔ / ⚠ / ● signs so a medior auditor scans fast.

const STATUS = {
  ok: { icon: Check, cls: 'text-sev-low', ring: 'ring-sev-low/25 bg-sev-low/10' },
  gap: { icon: AlertTriangle, cls: 'text-sev-med', ring: 'ring-sev-med/25 bg-sev-med/10' },
  empty: { icon: Circle, cls: 'text-fg-subtle', ring: 'ring-line bg-surface-3' },
}

export default function CoverageMatrix({ engagementId }) {
  const { data, isPending, isError, refetch, isFetching } = useQuery({
    queryKey: ['coverage', engagementId],
    queryFn: () => getCoverage(engagementId),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          <ShieldCheck size={16} className="text-brand" /> Coverage & consistency
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium text-fg-muted transition hover:bg-surface-3 disabled:opacity-50"
        >
          <RefreshCw size={13} className={isFetching ? 'animate-spin' : ''} /> Recheck
        </button>
      </div>

      {isPending && <div className="h-24 animate-pulse rounded-xl bg-surface-3" />}
      {isError && <p className="text-sm text-sev-high">Coverage check unavailable.</p>}

      {data && (
        <>
          <SummaryCard title="Assurance sweep" icon={ShieldCheck}>
            {data.summary}
          </SummaryCard>

          <ul className="space-y-2">
            {data.checks.map((c, i) => {
              const s = STATUS[c.status] || STATUS.empty
              const Icon = s.icon
              return (
                <li key={i} className="flex items-start gap-3 rounded-xl border border-line bg-surface p-3">
                  <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ring-1 ring-inset ${s.ring}`}>
                    <Icon size={14} className={s.cls} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-fg">{c.label}</div>
                    <div className="mt-0.5 text-xs text-fg-muted">{c.detail}</div>
                    {c.gap && (
                      <div className="mt-1.5 rounded-lg bg-sev-med/10 px-2 py-1 text-xs text-sev-med">
                        {c.gap}
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </>
      )}
    </div>
  )
}
