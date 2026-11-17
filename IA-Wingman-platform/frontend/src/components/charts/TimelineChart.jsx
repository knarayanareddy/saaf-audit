import { statusColor, statusLabel } from '../../lib/entities'

// A compact planning timeline: each engagement is a bar from start→end coloured
// by status, with diamond markers for draft/final report dates and a "today" rule.
const DAY = 86400000
const parse = (s) => (s ? new Date(s + 'T00:00:00') : null)
const fmtMonth = (d) => d.toLocaleDateString('en-GB', { month: 'short' })

export default function TimelineChart({ rows = [], onRowClick }) {
  const withDates = rows.filter((r) => r.start_date && r.end_date)
  if (withDates.length === 0) {
    return <div className="py-8 text-center text-sm text-fg-muted">No scheduled dates yet.</div>
  }

  // Window: a little padding around the min/max of all relevant dates.
  const all = withDates.flatMap((r) => [r.start_date, r.end_date, r.draft_report_date, r.final_report_date].filter(Boolean).map(parse))
  let min = new Date(Math.min(...all))
  let max = new Date(Math.max(...all))
  min = new Date(min.getTime() - 10 * DAY)
  max = new Date(max.getTime() + 10 * DAY)
  const span = Math.max(1, max - min)
  const pct = (d) => (((parse(typeof d === 'string' ? d : d) ?? min) - min) / span) * 100

  // Month gridlines
  const months = []
  const cur = new Date(min.getFullYear(), min.getMonth(), 1)
  while (cur <= max) {
    months.push(new Date(cur))
    cur.setMonth(cur.getMonth() + 1)
  }

  const today = new Date()
  const todayPct = today >= min && today <= max ? ((today - min) / span) * 100 : null

  const LABEL_W = 200

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        {/* Month header */}
        <div className="relative mb-1 h-5" style={{ marginLeft: LABEL_W }}>
          {months.map((m, i) => (
            <span key={i} className="absolute text-[11px] text-fg-subtle" style={{ left: `${pct(m.toISOString().slice(0, 10))}%` }}>
              {fmtMonth(m)}
            </span>
          ))}
        </div>

        <div className="relative">
          {/* gridlines + today */}
          <div className="pointer-events-none absolute inset-0" style={{ marginLeft: LABEL_W }}>
            {months.map((m, i) => (
              <span key={i} className="absolute inset-y-0 w-px bg-line" style={{ left: `${pct(m.toISOString().slice(0, 10))}%` }} />
            ))}
            {todayPct !== null && (
              <span className="absolute inset-y-0 w-px bg-brand/60" style={{ left: `${todayPct}%` }}>
                <span className="absolute -top-0.5 -translate-x-1/2 rounded bg-brand px-1 py-0.5 text-[9px] font-semibold text-brand-fg">now</span>
              </span>
            )}
          </div>

          <div className="space-y-1.5">
            {withDates.map((r) => {
              const left = pct(r.start_date)
              const width = Math.max(1.5, pct(r.end_date) - left)
              const color = statusColor(r.status)
              return (
                <button
                  key={r.id}
                  onClick={onRowClick ? () => onRowClick(r) : undefined}
                  className="group flex w-full items-center rounded-md py-0.5 text-left transition hover:bg-surface-3"
                  title={`${r.name} · ${statusLabel(r.status)}`}
                >
                  <span className="shrink-0 truncate pr-3 text-xs text-fg-muted group-hover:text-fg" style={{ width: LABEL_W }}>
                    {r.name}
                  </span>
                  <span className="relative h-5 flex-1">
                    <span
                      className="absolute top-1/2 h-3 -translate-y-1/2 rounded-full border"
                      style={{ left: `${left}%`, width: `${width}%`, background: statusColor(r.status, 0.28), borderColor: color }}
                    />
                    {[r.draft_report_date, r.final_report_date].filter(Boolean).map((d, i) => (
                      <span
                        key={i}
                        className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45 border"
                        style={{ left: `${pct(d)}%`, background: 'rgb(var(--surface))', borderColor: color }}
                        title={i === 0 ? 'Draft report' : 'Final report'}
                      />
                    ))}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
