import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Check, Circle } from 'lucide-react'
import { getAiShare } from '../../api/history'

// How much of this audit file IA Wingman proposed, and what people did with it.
// Two sources, never blended: the records themselves (who made each item, and
// whether a person accepted it) and the edit register (whether a person changed
// it later — only since the register started). Each number says which it is.

const AI = 'rgb(var(--share-ai))'
const AI_TINT = 'rgb(var(--share-ai) / 0.22)'

// Same hue for everything the platform proposed; texture, not a second colour,
// says how far the decision got — so the split survives colour blindness and print.
const SEGMENTS = [
  { key: 'accepted', label: 'Proposed, accepted', fill: { background: AI } },
  { key: 'open', label: 'Proposed, awaiting a decision',
    fill: { background: `repeating-linear-gradient(45deg, ${AI} 0 2px, ${AI_TINT} 2px 5px)` } },
  { key: 'no_step', label: 'Proposed, no sign-off step',
    fill: { background: `radial-gradient(${AI} 1.1px, ${AI_TINT} 1.4px) 0 0 / 5px 5px` } },
  { key: 'by_person', label: 'Entered by a person', fill: { background: 'rgb(var(--share-person))' } },
  { key: 'no_run_recorded', label: 'No AI run recorded', fill: { background: 'rgb(var(--share-unknown))' } },
]

const KIND_PAGE = {
  racm_objectives: 'racm', racm_risks: 'racm', racm_controls: 'racm', racm_tests: 'racm',
  racm_evidence: 'racm', scope_decisions: 'racm',
  applicable_frameworks: 'planning/framework-requirements',
  scope_items: 'planning/scope-objectives', key_audit_questions: 'planning/scope-objectives',
  fieldwork_observations: 'fieldwork', findings: 'reporting',
}

const DOC_PAGE = {
  topic_intelligence: 'planning/topic-intelligence', process_notes: 'planning/process-understanding',
  background_risk_assessments: 'planning/bra', audit_notification_letters: 'planning/anl',
  kickoff_agendas: 'planning/kickoff', work_programs: 'planning/work-program',
  interview_guides: 'planning/interview', audit_reports: 'reporting',
}

const OUTCOMES = [
  ['unchanged', 'kept as proposed'],
  ['changed_by_person', 'changed by a person'],
  ['rejected', 'rejected'],
  ['superseded', 'replaced by a re-run'],
  ['created_by_person', 'made by a person'],
]

function parts(k) {
  const decided = k.has_decision ?? true
  return {
    accepted: k.accepted,
    open: k.open,
    no_step: decided ? Math.max(0, k.proposed - k.accepted - k.open) : k.proposed,
    by_person: k.by_person,
    no_run_recorded: k.no_run_recorded,
  }
}

const total = (c) => SEGMENTS.reduce((n, s) => n + c[s.key], 0)

// `scale` is the largest total among the bars being compared, so a kind with 13
// items is drawn shorter than one with 57 — length is the count, not a 100% stack.
function Bar({ counts, label, height = 'h-2.5', scale }) {
  const shown = SEGMENTS.filter((s) => counts[s.key] > 0)
  if (!shown.length) return null
  const width = scale ? `${Math.max(2, (100 * total(counts)) / scale)}%` : '100%'
  return (
    <div className="flex gap-[2px]" style={{ width }} role="img"
         aria-label={`${label}: ${shown.map((s) => `${counts[s.key]} ${s.label.toLowerCase()}`).join(', ')}`}>
      {shown.map((s, i) => (
        <div key={s.key} className="group relative py-1" style={{ flex: counts[s.key] }}>
          <div
            className={`${height} ${i === 0 ? 'rounded-l' : ''} ${i === shown.length - 1 ? 'rounded-r' : ''}`}
            style={s.fill}
          />
          <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-line bg-surface-raised px-2 py-1 text-xs text-fg shadow-sm group-hover:block">
            <span className="font-semibold">{counts[s.key]}</span> {s.label.toLowerCase()}
            <span className="text-fg-subtle"> · {label}</span>
          </span>
        </div>
      ))}
    </div>
  )
}

function Legend({ counts }) {
  return (
    <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-muted">
      {SEGMENTS.filter((s) => counts[s.key] > 0).map((s) => (
        <li key={s.key} className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={s.fill} />
          {s.label} <span className="font-semibold text-fg">{counts[s.key]}</span>
        </li>
      ))}
    </ul>
  )
}

function Headline({ h }) {
  const total = h.proposed + h.by_person + h.no_run_recorded
  if (!total) return <p className="text-sm text-fg-muted">This file holds no items yet.</p>
  return (
    <p className="text-sm text-fg">
      {h.proposed === total
        ? <>IA Wingman proposed {total === 1 ? 'the only item' : <>all <span className="font-semibold">{total}</span> items</>} in this file.</>
        : <>IA Wingman proposed <span className="font-semibold">{h.proposed}</span> of the{' '}
            <span className="font-semibold">{total}</span> items in this file.</>}
      {h.accepted + h.open > 0 && (
        <> People accepted {h.accepted}; {h.open ? `${h.open} still ${h.open === 1 ? 'awaits' : 'await'} a decision` : 'none await a decision'}.</>
      )}
      {h.by_person > 0 && <> {h.by_person} {h.by_person === 1 ? 'was' : 'were'} entered by a person.</>}
      {h.no_run_recorded > 0 && <> For {h.no_run_recorded}, no AI run is on record, so who wrote {h.no_run_recorded === 1 ? 'it' : 'them'} is not known.</>}
    </p>
  )
}

function RegisterBlock({ register, basis }) {
  const since = register.recorded_since ? new Date(register.recorded_since).toLocaleDateString() : null
  if (basis === 'records') {
    return (
      <p className="text-xs text-fg-muted">
        The edit register has recorded changes {since ? `since ${since}` : 'from today'}; nothing in this file has
        changed since then. The counts above come from the records themselves — they show who made each item,
        not whether a person edited it later.
      </p>
    )
  }
  return (
    <div>
      <p className="text-xs text-fg-muted">
        Since {since}, the edit register saw what happened to each item. Items from before then are counted above
        only.
      </p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[30rem] text-xs">
          <thead>
            <tr className="text-left text-fg-subtle">
              <th className="py-1 pr-3 font-medium">Kind</th>
              {OUTCOMES.map(([k, l]) => <th key={k} className="py-1 pr-3 text-right font-medium">{l}</th>)}
            </tr>
          </thead>
          <tbody>
            {register.kinds.map((k) => (
              <tr key={k.key} className="border-t border-line-subtle">
                <td className="py-1 pr-3 text-fg">{k.label}</td>
                {OUTCOMES.map(([o]) => (
                  <td key={o} className={`py-1 pr-3 text-right tabular-nums ${k[o] ? 'text-fg' : 'text-fg-subtle'}`}>
                    {k[o] || '–'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function AiSharePanel({ engagementId }) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['ai-share', engagementId],
    queryFn: () => getAiShare(engagementId),
  })

  if (isPending) return <div className="h-40 animate-pulse rounded-xl bg-surface-3" />
  if (isError) return <p className="text-sm text-sev-high">The AI share could not be loaded.</p>

  // Across the file, what is proposed but neither accepted nor open belongs to
  // kinds without a decision step — the same split as one kind with a step.
  const headline = parts({ ...data.headline, has_decision: true })
  const largest = Math.max(1, ...data.kinds.map((k) => total(parts(k))))

  return (
    <div className="space-y-5">
      <div>
        <Headline h={data.headline} />
        <div className="mt-3"><Bar counts={headline} label="Whole file" height="h-3" /></div>
        <Legend counts={headline} />
      </div>

      {data.kinds.length > 0 && (
        <div className="border-t border-line pt-4">
          <h3 className="text-caption">By kind</h3>
          <ul className="mt-2 divide-y divide-line-subtle">
            {data.kinds.map((k) => {
              const c = parts(k)
              const page = KIND_PAGE[k.key]
              return (
                <li key={k.key} className="py-2">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
                    <span className="text-sm text-fg">{k.label}</span>
                    <span className="flex items-center gap-3 text-xs text-fg-muted">
                      <span className="tabular-nums">
                        {k.proposed} proposed
                        {k.has_decision && k.proposed > 0 && <> · {k.accepted} accepted</>}
                        {k.by_person > 0 && <> · {k.by_person} by a person</>}
                        {k.no_run_recorded > 0 && <> · {k.no_run_recorded} without an AI run on record</>}
                      </span>
                      {page && (
                        <Link to={`/engagements/${engagementId}/${page}`} className="font-medium text-brand hover:underline">
                          Review →
                        </Link>
                      )}
                    </span>
                  </div>
                  <Bar counts={c} label={k.label} scale={largest} />
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {data.documents.length > 0 && (
        <div className="border-t border-line pt-4">
          <h3 className="text-caption">Documents</h3>
          <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {data.documents.map((d) => {
              const page = DOC_PAGE[d.key]
              const Name = page ? Link : 'span'
              return (
                <li key={d.key} className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1 rounded-lg bg-surface-2 px-3 py-2">
                  <div className="min-w-0">
                    <Name {...(page ? { to: `/engagements/${engagementId}/${page}` } : {})}
                          className={`text-sm text-fg ${page ? 'hover:text-brand hover:underline' : ''}`}>
                      {d.label}
                    </Name>
                    <div className="mt-0.5 flex items-center gap-1.5 text-xs text-fg-muted">
                      <span className="inline-block h-2 w-2 rounded-sm"
                            style={{ background: d.written_by === 'ai' ? AI : 'rgb(var(--share-unknown))' }} />
                      {d.written_by === 'ai' ? 'AI draft, run on record' : 'No AI run recorded'}
                    </div>
                  </div>
                  {d.decision && (
                    <span className={`flex items-center gap-1 text-xs ${d.decision.done ? 'text-fg' : 'text-fg-subtle'}`}>
                      {d.decision.done ? <Check size={13} className="text-sev-low" /> : <Circle size={11} />}
                      {d.decision.done ? d.decision.step : `${d.decision.step} pending`}
                    </span>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <div className="border-t border-line pt-4">
        <h3 className="text-caption">Changes since the register started</h3>
        <div className="mt-2"><RegisterBlock register={data.register} basis={data.basis} /></div>
      </div>
    </div>
  )
}
