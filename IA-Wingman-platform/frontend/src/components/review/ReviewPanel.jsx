import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, X, Sparkles, Loader2, ClipboardCheck } from 'lucide-react'
import { getReview, runReview, patchReviewComment } from '../../api/review'
import Segmented from '../ui/Segmented'
import Collapsible from '../ui/Collapsible'
import { SummaryCard } from '../ui/ReadableOutput'
import { SeverityTag } from '../ui/Provenance'
import Tooltip from '../ui/Tooltip'

// Opt-in QA Reviewer — an AI agent that critiques another agent's artifact.
// Human-in-the-loop: every comment is a proposal the auditor accepts or dismisses.
// Renders in the readable-output system: summary first, then collapsible
// must-fix / suggestion lists with severity signs.

const ARTIFACTS = [
  { value: 'peer_review', label: 'Peer review' },
  { value: 'topic_intelligence', label: 'Topic Intelligence' },
  { value: 'scope', label: 'Scope' },
  { value: 'frameworks', label: 'Frameworks' },
  { value: 'coherence', label: 'Coherence' },
]

const QUALITY = {
  good: { label: 'Good', cls: 'text-sev-low' },
  adequate: { label: 'Adequate', cls: 'text-sev-med' },
  needs_work: { label: 'Needs work', cls: 'text-sev-high' },
}

// What the run cost. Not decoration: an auditor signing off AI-assisted work
// should be able to see which model produced it and what was spent, and a
// "judge" tier that reasoned before answering is a different provenance claim
// from a quick suggestion. The backend prices it (services/model_tiers.py); a
// model with no price configured reads as such rather than as free.
function RunReceipt({ run }) {
  if (!run) return null
  const money = run.cost_usd == null
    ? 'cost not priced'
    : run.cost_usd < 0.01 ? `$${run.cost_usd.toFixed(4)}` : `$${run.cost_usd.toFixed(2)}`
  const bits = [
    run.tier ? `${run.tier} tier` : null,
    run.model,
    `${(run.duration_ms / 1000).toFixed(1)}s`,
    `${run.input_tokens?.toLocaleString()} in / ${run.output_tokens?.toLocaleString()} out`,
    run.thinking_tokens ? `${run.thinking_tokens.toLocaleString()} reasoning` : run.reasoned ? "reasoning not shown" : null,
    run.cached_tokens ? `${run.cached_tokens.toLocaleString()} cached` : null,
    money,
    run.repaired ? 'schema corrected on retry' : null,
  ].filter(Boolean)
  return <div className="mt-2 text-[11px] text-fg-subtle">{bits.join(' \u00b7 ')}</div>
}

// GIAS peer-review ratings: generally / partially / not compliant — plus NA for
// a criterion this platform holds no record of (a closing meeting happens in a
// room). NA is deliberately neutral and is left out of the score: rating it NC
// would blame the audit for what the tool never tracked.
const RATING = {
  gc: { label: 'GC', cls: 'bg-sev-low/12 text-sev-low ring-sev-low/25', title: 'Generally conforms — the file meets this GIAS requirement' },
  pc: { label: 'PC', cls: 'bg-sev-med/12 text-sev-med ring-sev-med/25', title: 'Partially conforms — the file meets part of this GIAS requirement' },
  nc: { label: 'NC', cls: 'bg-sev-high/12 text-sev-high ring-sev-high/25', title: 'Does not conform — the file does not meet this GIAS requirement' },
  na: { label: 'NA', cls: 'bg-surface-3 text-fg-subtle ring-line', title: 'Not assessable from this platform — verify outside the tool' },
}

function CriteriaTable({ criteria }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <ul className="divide-y divide-line">
        {criteria.map((c) => {
          const r = RATING[(c.rating || 'nc').toLowerCase()] || RATING.nc
          return (
            <li key={c.nr} className="flex items-start gap-3 py-2">
              <Tooltip label={r.title} side="right" width="15rem" className="mt-0.5 shrink-0">
                <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-bold ring-1 ring-inset ${r.cls}`}>{r.label}</span>
              </Tooltip>
              <div className="min-w-0 flex-1">
                <div className="text-sm text-fg">{c.nr}. {c.title}</div>
                <div className="text-[11px] uppercase tracking-wide text-fg-subtle">GIAS {c.gias}</div>
                {c.comment && <div className="mt-0.5 text-xs text-fg-muted">{c.comment}</div>}
                {c.evidence && <div className="mt-0.5 text-xs text-fg-subtle">Evidence: {c.evidence}</div>}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function CommentRow({ engagementId, artifact, comment }) {
  const qc = useQueryClient()
  const mutate = useMutation({
    mutationFn: (payload) => patchReviewComment(engagementId, artifact, comment.id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review', engagementId, artifact] }),
  })
  const dismissed = comment.is_dismissed
  const accepted = comment.is_accepted
  return (
    <li className={`rounded-xl border border-line bg-surface p-3 transition ${dismissed ? 'opacity-50' : ''}`}>
      <div className="flex items-start gap-2">
        <SeverityTag level={comment.severity} />
        <div className="min-w-0 flex-1">
          {comment.section && <div className="text-[11px] font-medium uppercase tracking-wide text-fg-subtle">{comment.section}</div>}
          <div className={`text-sm text-fg ${dismissed ? 'line-through' : ''}`}>{comment.comment}</div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <button
          onClick={() => mutate.mutate({ is_accepted: !accepted, is_dismissed: false })}
          className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition ${
            accepted ? 'bg-sev-low/15 text-sev-low' : 'text-fg-muted hover:bg-surface-3'
          }`}
        >
          <Check size={13} /> {accepted ? 'Accepted' : 'Accept'}
        </button>
        <button
          onClick={() => mutate.mutate({ is_dismissed: !dismissed, is_accepted: false })}
          className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition ${
            dismissed ? 'bg-surface-3 text-fg' : 'text-fg-muted hover:bg-surface-3'
          }`}
        >
          <X size={13} /> {dismissed ? 'Dismissed' : 'Dismiss'}
        </button>
      </div>
    </li>
  )
}

const PEER_PHASES = [
  { value: 'total', label: 'Total' },
  { value: 'planning', label: 'Planning' },
  { value: 'fieldwork', label: 'Fieldwork' },
  { value: 'reporting', label: 'Reporting' },
]
const PHASE_LABEL = Object.fromEntries(PEER_PHASES.map((p) => [p.value, p.label]))

export default function ReviewPanel({ engagementId }) {
  const [artifact, setArtifact] = useState('peer_review')
  const [phase, setPhase] = useState('total')
  const qc = useQueryClient()

  const { data } = useQuery({
    queryKey: ['review', engagementId, artifact],
    queryFn: () => getReview(engagementId, artifact),
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 2500 : false),
  })

  const run = useMutation({
    mutationFn: () => runReview(engagementId, artifact, phase),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review', engagementId, artifact] }),
  })

  const status = data?.status
  const running = status === 'running' || run.isPending
  const result = data?.result
  const comments = result?.comments || []
  const mustFix = comments.filter((c) => c.severity === 'must_fix')
  const suggestions = comments.filter((c) => c.severity !== 'must_fix')
  const quality = QUALITY[result?.overall_quality]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          <ClipboardCheck size={16} className="text-brand" /> Peer Reviewer
        </div>
        {artifact === 'peer_review'
          ? <Segmented options={PEER_PHASES} value={phase} onChange={setPhase} size="sm" />
          : <Segmented options={ARTIFACTS} value={artifact} onChange={setArtifact} size="sm" />}
      </div>

      <button
        onClick={() => run.mutate()}
        disabled={running}
        className="inline-flex items-center gap-2 rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
      >
        {running ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
        {running ? 'Reviewing…' : status === 'ready'
          ? `Re-run review${phase !== 'total' ? ` · ${PHASE_LABEL[phase]}` : ''}`
          : artifact === 'peer_review'
            ? (phase === 'total' ? 'Run peer review' : `Run ${PHASE_LABEL[phase]} peer review`)
            : 'Run quality review'}
      </button>
      {artifact === 'peer_review' && status !== 'ready' && !running && (
        <p className="text-xs text-fg-subtle">
          Independent GIAS peer-review checklist. Review the whole engagement (12 criteria) or one phase —
          Planning (GIAS 13), Fieldwork (GIAS 14) or Reporting (GIAS 15). It reads the audit file itself —
          the letter, the risk assessment, the work program, the tests and their evidence, the findings —
          and proposes a rating per criterion. You confirm them.
        </p>
      )}

      {status === 'no_data' && (
        <p className="text-sm text-fg-muted">{result?.summary || 'Nothing to review yet — generate this artifact first.'}</p>
      )}
      {status === 'failed' && <p className="text-sm text-sev-high">{result?.summary || 'Review failed.'}</p>}

      {status === 'ready' && result && (
        <>
          <SummaryCard title="Reviewer assessment" icon={ClipboardCheck}>
            {quality && <span className={`font-semibold ${quality.cls}`}>{quality.label}. </span>}
            {result.summary}
          </SummaryCard>

          {typeof result.percentage === 'number' && (
            <div className="flex items-center gap-3 rounded-xl border border-line bg-surface p-3">
              <div className="text-2xl font-semibold tabular-nums text-brand">
                {result.total_score}/{result.max_score}
              </div>
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-surface-3">
                  <div className={`h-full rounded-full ${result.percentage >= 75 ? 'bg-sev-low/100' : result.percentage >= 50 ? 'bg-sev-med/100' : 'bg-sev-high/100'}`} style={{ width: `${result.percentage}%` }} />
                </div>
                <p className="mt-1 text-xs text-fg-subtle">
                  {result.phase && result.phase !== 'total' ? `${PHASE_LABEL[result.phase] || result.phase} phase · ` : ''}
                  GIAS peer-review score · {result.percentage}% · proposed, pending human confirmation
                  {result.not_assessable > 0 && ` · ${result.not_assessable} ${result.not_assessable === 1 ? 'criterion' : 'criteria'} outside the score (no record in this platform)`}
                </p>
              </div>
            </div>
          )}

          <RunReceipt run={result.run} />

          {result.criteria?.length > 0 && (
            <Collapsible title="GIAS criteria" count={result.criteria.length} defaultOpen>
              <CriteriaTable criteria={result.criteria} />
            </Collapsible>
          )}

          {mustFix.length > 0 && (
            <Collapsible title="Must fix" count={mustFix.length} defaultOpen>
              <ul className="space-y-2">
                {mustFix.map((c) => (
                  <CommentRow key={c.id} engagementId={engagementId} artifact={artifact} comment={c} />
                ))}
              </ul>
            </Collapsible>
          )}
          {suggestions.length > 0 && (
            <Collapsible title="Suggestions" count={suggestions.length}>
              <ul className="space-y-2">
                {suggestions.map((c) => (
                  <CommentRow key={c.id} engagementId={engagementId} artifact={artifact} comment={c} />
                ))}
              </ul>
            </Collapsible>
          )}
          {comments.length === 0 && <p className="text-sm text-fg-muted">No issues flagged — the artifact reads well.</p>}
        </>
      )}
    </div>
  )
}
