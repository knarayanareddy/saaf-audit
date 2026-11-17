import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  ShieldCheck, ChevronRight, Sparkles, Loader2, Check, TriangleAlert, X,
  CircleHelp, Lightbulb, Quote, ShieldAlert,
} from 'lucide-react'
import { getValidation, judgeValidation } from '../../api/reporting'
import ConfirmDialog from '../ui/ConfirmDialog'
import { useStore } from '../../store/useStore'

// Grounded validator — the content-level second opinion. Where the explainability
// annex asks "is this finding traceable?", this asks "does the source actually SAY
// this?" It re-reads the source behind each 5C claim and returns supported /
// partial / unsupported with a VERBATIM quote. The auditor reviews only the reds.

const VERDICT = {
  unsupported: { label: 'Not in source', Icon: X, rail: 'border-l-sev-high', chip: 'text-sev-high bg-sev-high/10 ring-sev-high/25', order: 0 },
  partial: { label: 'Partly', Icon: TriangleAlert, rail: 'border-l-sev-med', chip: 'text-sev-med bg-sev-med/10 ring-sev-med/25', order: 1 },
  no_source: { label: 'No source', Icon: CircleHelp, rail: 'border-l-line-strong', chip: 'text-fg-muted bg-surface-3 ring-line', order: 2 },
  judgement: { label: 'Judgement', Icon: Lightbulb, rail: 'border-l-brand', chip: 'text-brand bg-brand/10 ring-brand/25', order: 3 },
  supported: { label: 'In source', Icon: Check, rail: 'border-l-sev-low', chip: 'text-sev-low bg-sev-low/10 ring-sev-low/25', order: 4 },
}

const FOUND_MAP = { yes: 'supported', partial: 'partial', no: 'unsupported' }
const CONF = { high: 'High', medium: 'Med', low: 'Low' }

function effectiveVerdict(claim) {
  const ai = claim.ai
  if (ai && ai.found) {
    const v = FOUND_MAP[ai.found] || claim.verdict
    // cause/recommendation are the auditor's reasoning — "not in source" is expected there.
    if ((claim.claim_kind === 'judgement' || claim.claim_kind === 'forward') && (v === 'unsupported' || v === 'partial')) return 'judgement'
    return v
  }
  return claim.verdict
}

function ClaimRow({ claim }) {
  const eff = effectiveVerdict(claim)
  const v = VERDICT[eff] || VERDICT.no_source
  const VIcon = v.Icon
  const ai = claim.ai
  // The AI verdict is authoritative; the deterministic best-match is the free view.
  const quote = ai?.quote || claim.best_match?.quote
  const sourceLabel = ai?.source_label || claim.best_match?.source_label
  const isLexical = !ai?.quote && !!claim.best_match?.quote

  return (
    <div className={`rounded-r-lg border-l-[3px] bg-surface-2 py-2 pl-3 pr-3 ${v.rail}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${v.chip}`}>
          <VIcon size={11} /> {v.label}
        </span>
        <span className="text-sm font-semibold text-fg">{claim.label}</span>
        {ai?.confidence && (
          <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[10px] font-medium text-fg-muted">{CONF[ai.confidence] || ai.confidence} confidence</span>
        )}
        {ai?.quote_unverified && (
          <span className="inline-flex items-center gap-1 rounded bg-sev-med/10 px-1.5 py-0.5 text-[10px] font-medium text-sev-med ring-1 ring-inset ring-sev-med/25" title="The AI could not point to a verbatim quote — treat with care">
            <ShieldAlert size={10} /> unverified
          </span>
        )}
      </div>

      <p className="mt-1 text-sm text-fg-muted">{claim.claim_text}</p>

      {quote && (
        <figure className="mt-1.5 border-l-2 border-line pl-2.5">
          <blockquote className="flex gap-1.5 text-[13px] italic text-fg">
            <Quote size={12} className="mt-1 shrink-0 text-fg-subtle" />
            <span>“{quote}”</span>
          </blockquote>
          <figcaption className="mt-0.5 text-[11px] text-fg-subtle">
            {sourceLabel}{isLexical ? ' · lexical match — verify' : ''}
          </figcaption>
        </figure>
      )}
      {!quote && eff === 'no_source' && (
        <p className="mt-1 text-[11px] text-fg-subtle">No linked test, evidence or observation to check this claim against.</p>
      )}
      {ai?.note && <p className="mt-1 text-[11px] text-fg-subtle">{ai.note}</p>}
    </div>
  )
}

function ValidatorBody({ engagementId, findingId }) {
  const showToast = useStore((s) => s.showToast)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [judging, setJudging] = useState(false)
  const [prevJudgedAt, setPrevJudgedAt] = useState(null)

  const { data, isPending } = useQuery({
    queryKey: ['validation', engagementId, findingId],
    queryFn: () => getValidation(engagementId, findingId),
    refetchInterval: judging ? 2000 : false,
  })

  const judge = useMutation({
    mutationFn: () => judgeValidation(engagementId, findingId),
    onSuccess: () => { setConfirmOpen(false); setPrevJudgedAt(data?.judged_at || null); setJudging(true) },
  })

  useEffect(() => {
    if (judging && data?.judged_at && data.judged_at !== prevJudgedAt) {
      setJudging(false)
      showToast('Claims validated by AI')
    }
  }, [judging, data?.judged_at, prevJudgedAt, showToast])

  if (isPending || !data) {
    return <div className="flex items-center gap-2 py-4 text-sm text-fg-muted"><Loader2 size={14} className="animate-spin" /> Reading the source…</div>
  }

  const h = data.headline || {}
  const claims = [...(data.claims || [])].sort((a, b) => (VERDICT[effectiveVerdict(a)]?.order ?? 9) - (VERDICT[effectiveVerdict(b)]?.order ?? 9))
  const needs = h.needs_review || 0

  return (
    <div className="mt-3 rounded-xl border border-brand/20 bg-brand-faint/50 p-4">
      <div className="flex items-center gap-1.5 text-caption text-brand">
        <ShieldCheck size={13} /> {data.reference}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className={`text-sm font-semibold ${needs > 0 ? 'text-sev-med' : 'text-sev-low'}`}>
          {needs > 0 ? `${needs} of ${h.total} claims need your review` : `All ${h.total} claims trace to the source`}
        </span>
        <span className="text-fg-subtle">·</span>
        {['supported', 'partial', 'unsupported', 'no_source', 'judgement'].filter((k) => h[k]).map((k) => {
          const v = VERDICT[k]
          return (
            <span key={k} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${v.chip}`}>
              {h[k]} {v.label}
            </span>
          )
        })}
      </div>

      {!data.has_source && (
        <p className="mt-2 text-[12px] text-fg-subtle">This finding has no linked test, evidence or observation, so there is nothing to validate its factual claims against yet.</p>
      )}

      <div className="mt-3 space-y-2">
        {claims.map((c) => <ClaimRow key={c.key} claim={c} />)}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          onClick={() => setConfirmOpen(true)}
          disabled={judging || !data.has_source}
          title={!data.has_source ? 'No source attached to validate against' : undefined}
          className="inline-flex items-center gap-1.5 rounded-lg border border-brand/30 px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
        >
          {judging ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {judging ? 'Validating…' : 'Validate with AI'}
        </button>
        {data.judged_at && (
          <span className="text-[11px] text-fg-subtle">
            AI-validated{data.judge_stale ? ' · may lag recent edits' : ''}
          </span>
        )}
      </div>
      <p className="mt-2 text-[11px] text-fg-subtle">
        A second opinion — the AI re-reads the source and every quote is verified word-for-word against it. You decide.
      </p>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => judge.mutate()}
        title="Validate the claims with AI?"
        description="The AI re-reads the source behind this finding and judges each claim, returning a verbatim quote where it is supported. It uses AI budget, introduces no new facts, and every quote is verified against the source."
        confirmLabel="Validate — uses AI"
        loading={judge.isPending}
      />
    </div>
  )
}

export default function GroundedValidator({ engagementId, findingId }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-lg px-1 py-1 text-left text-sm font-medium text-fg transition hover:text-brand"
      >
        <ShieldCheck size={15} className="text-brand" />
        Grounded validation
        <span className="rounded-full bg-brand-subtle px-1.5 py-0.5 text-[10px] font-semibold text-brand">does the source say this?</span>
        <ChevronRight size={15} className={`ml-auto text-fg-subtle transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && <ValidatorBody engagementId={engagementId} findingId={findingId} />}
    </div>
  )
}
