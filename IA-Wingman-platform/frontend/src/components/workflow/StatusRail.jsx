import { Check, ShieldCheck } from 'lucide-react'

// The five engagement statuses as one rail. With a current status it shows where
// the audit is; without one it simply reads as the lifecycle.
//
// Between Reporting and Closed sits the quality gate. It is deliberately NOT a
// pill: quality is not a status an audit can be in — it is a check that has to
// pass before the audit may close. Drawing it as a marker on the line says that,
// where a sixth pill would have claimed it was a phase of its own.
export default function StatusRail({ statuses, current }) {
  const index = statuses.findIndex((s) => s.key === current)
  const closedIndex = statuses.findIndex((s) => s.key === 'closed')

  return (
    <ol className="flex items-center gap-2 overflow-x-auto pb-1" aria-label="Engagement lifecycle">
      {statuses.map((s, i) => {
        const done = index >= 0 && i < index
        const now = i === index
        // The gate belongs in front of "Closed": an audit is signed off only
        // after quality has had its say.
        const gateHere = i === closedIndex && closedIndex > 0
        const gatePassed = index >= 0 && index >= closedIndex
        return (
          <li key={s.key} className="flex shrink-0 items-center gap-2" aria-current={now ? 'step' : undefined}>
            {i > 0 && <span className={`h-px w-5 sm:w-8 ${done || now ? 'bg-brand/50' : 'bg-line'}`} aria-hidden="true" />}
            {gateHere && (
              <>
                <span
                  title="Quality checks — coverage, AI review and peer review — run before an audit can close"
                  className={`inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-[11px] font-medium ring-1 ring-inset ${
                    gatePassed ? 'text-brand ring-brand/35' : 'text-fg-subtle ring-line'
                  }`}
                >
                  <ShieldCheck size={11} aria-hidden="true" />
                  Quality check
                </span>
                <span className={`h-px w-5 sm:w-8 ${gatePassed ? 'bg-brand/50' : 'bg-line'}`} aria-hidden="true" />
              </>
            )}
            <span
              className={`inline-flex h-6 items-center gap-1.5 rounded-md px-2 text-[11px] font-medium ${
                now ? 'bg-brand text-brand-fg' : done ? 'bg-brand-subtle text-brand' : 'bg-surface-2 text-fg-subtle ring-1 ring-inset ring-line'
              }`}
            >
              {done && <Check size={11} aria-hidden="true" />}
              {now && (
                <span className="relative flex h-2 w-2" aria-hidden="true">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-fg/70" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-fg" />
                </span>
              )}
              {s.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
