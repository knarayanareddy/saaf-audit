import { Sparkles, UserCheck, Lock } from 'lucide-react'
import { STATUS, METHOD_META } from './WorkflowNode'
import { waitingOn } from '../../lib/workflowLayout'

// Narrow-screen version of the map: the same phases, stages, states and gates
// as a vertical timeline per phase.
export default function WorkflowList({ layout, wf, live, activeKeys, focusKeys, currentBand, onSelect }) {
  const gateByStage = Object.fromEntries((wf.human_gates || []).map((g) => [g.stage, g]))
  return (
    <div className="space-y-5">
      {layout.bands.map((band) => {
        const members = layout.nodes.filter((n) => n.band === band.key)
        const current = band.key === currentBand
        return (
          <section
            key={band.key}
            aria-label={band.label}
            className={`rounded-lg border p-3 ${current ? 'border-brand/25 bg-brand-faint' : 'border-line bg-surface-2'}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <h2 className={`text-[10px] font-medium uppercase tracking-[0.07em] ${current ? 'text-brand' : 'text-fg-muted'}`}>{band.label}</h2>
              {current && <span className="rounded bg-brand px-1 text-[9px] font-semibold uppercase leading-4 tracking-wide text-brand-fg">Current</span>}
              {live && <span className="ml-auto text-[11px] tabular-nums text-fg-subtle">{band.done}/{band.total}</span>}
            </div>
            <p className="mt-1 text-meta">{band.summary}</p>

            <ol className="relative ml-2.5 mt-3 space-y-2 border-l border-line pl-5">
              {members.map((n) => {
                const meta = live ? STATUS[n.status] || STATUS.available : METHOD_META
                const Icon = !live && n.ai ? Sparkles : meta.icon
                const waiting = live ? waitingOn(n, layout.byKey) : []
                const pending = live ? n.pending_decisions || 0 : 0
                const isNext = live && wf.next_gate === n.key
                const gate = gateByStage[n.key]
                const dimmed = activeKeys && !activeKeys.has(n.key)
                const focused = focusKeys?.has(n.key)
                return (
                  <li key={n.key} className={`relative transition-opacity duration-300 ${dimmed ? 'opacity-35' : ''}`}>
                    <span
                      aria-hidden="true"
                      className={`absolute -left-[30px] top-2.5 flex h-4 w-4 items-center justify-center rounded-full bg-surface ring-4 ${current ? 'ring-brand-faint' : 'ring-surface-2'} ${meta.dot}`}
                    >
                      <Icon size={11} className={meta.spin ? 'animate-spin' : ''} />
                    </span>
                    <button
                      type="button"
                      data-node={n.key}
                      onClick={() => onSelect(n)}
                      className={`flex w-full flex-col items-start rounded-lg border bg-surface px-3 py-2 text-left transition-colors duration-150 hover:border-line-strong focus:outline-none focus-visible:shadow-ring ${meta.card} ${
                        isNext ? 'wf-glow' : ''
                      } ${focused ? 'wf-focus border-brand/60' : ''}`}
                    >
                      <span className="flex w-full items-start gap-2">
                        <span className="min-w-0 flex-1 text-[13px] font-medium text-fg">{n.label}</span>
                        {isNext && (
                          <span className="shrink-0 rounded bg-sev-med px-1 text-[9px] font-semibold uppercase leading-4 tracking-wide text-canvas">Next</span>
                        )}
                        {pending > 0 && (
                          <span className="flex h-4 min-w-4 shrink-0 items-center justify-center rounded bg-sev-med px-1 text-[10px] font-semibold tabular-nums leading-none text-canvas">
                            {pending}
                          </span>
                        )}
                      </span>
                      <span className="mt-0.5 flex items-center gap-1 text-meta">
                        {n.ai && <Sparkles size={10} className="shrink-0 text-brand" />}
                        {n.agent}{live ? ` · ${meta.label}` : ''}
                      </span>
                      <span className="mt-1 text-xs leading-5 text-fg-muted">{live ? n.detail || n.description : n.description}</span>
                      {waiting.length > 0 && (
                        <span className="mt-1 inline-flex items-center gap-1 text-meta">
                          <Lock size={10} className="shrink-0" /> Waiting on {waiting.join(', ')}
                        </span>
                      )}
                      {gate && (
                        <span className="mt-1.5 inline-flex h-5 items-center gap-1 rounded bg-brand/10 px-1.5 text-[11px] font-medium text-brand">
                          <UserCheck size={10} className="shrink-0" /> {gate.label}
                        </span>
                      )}
                    </button>
                  </li>
                )
              })}
            </ol>
          </section>
        )
      })}
    </div>
  )
}
