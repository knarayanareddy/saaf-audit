import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ScrollText, ChevronRight, ShieldCheck, Sparkles, Loader2, Check, Minus,
  FileText, Database, MessagesSquare, Eye, Brain, Globe, Info, AlertTriangle, Search,
} from 'lucide-react'
import { getExplainability, sharpenExplainability } from '../../api/reporting'
import ConfirmDialog from '../ui/ConfirmDialog'
import { useStore } from '../../store/useStore'
import DefensibilityMeter from '../charts/DefensibilityMeter'

// The Explainability Annex — a defensible, traceable account of how a finding was
// reached, anchored in EU AI Act Art. 13/14 (transparency + human oversight).
// Built deterministically from the 5C + RACM spine; an opt-in AI step only
// rephrases the answers (never adds facts).

const SIGN = {
  ok: { Icon: Check, cls: 'text-sev-low' },
  gap: { Icon: AlertTriangle, cls: 'text-sev-med' },
  info: { Icon: Info, cls: 'text-fg-subtle' },
  check: { Icon: Search, cls: 'text-brand' },
}

// Evidence kind is carried by the ICON, not by a hue — six colours here said
// nothing a reader could decode, and made the annex look like a pie chart.
const KIND_CLS = 'text-fg-muted bg-surface-3 ring-line'
const KIND = {
  document: { Icon: FileText, cls: KIND_CLS },
  data: { Icon: Database, cls: KIND_CLS },
  interview: { Icon: MessagesSquare, cls: KIND_CLS },
  observation: { Icon: Eye, cls: KIND_CLS },
  model: { Icon: Brain, cls: KIND_CLS },
  web: { Icon: Globe, cls: KIND_CLS },
}

function GroundingChip({ kind, label }) {
  const k = KIND[kind] || KIND.model
  const Icon = k.Icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${k.cls}`}>
      <Icon size={11} /> {label}
    </span>
  )
}

// The O→R→C→T→E lineage as connected pills. Neutral on purpose: the letter
// prefix already names the stage, so five unrelated hues added noise, not meaning.
const REF_TONE = () => 'text-fg-muted border-line-strong'

function GroundingTrail({ trail }) {
  if (!trail?.length) return null
  return (
    <div className="flex flex-wrap items-center gap-1">
      {trail.map((ref, i) => (
        <span key={`${ref}-${i}`} className="flex items-center gap-1">
          <span className={`rounded-md border bg-surface px-1.5 py-0.5 text-[11px] font-bold ${REF_TONE(ref)}`}>{ref}</span>
          {i < trail.length - 1 && <ChevronRight size={12} className="text-fg-subtle" />}
        </span>
      ))}
    </div>
  )
}

// Lazily fetched: only queries when expanded, so a page of findings stays light.
function AnnexBody({ engagementId, findingId }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [sharpening, setSharpening] = useState(false)
  const [prevSharpenedAt, setPrevSharpenedAt] = useState(null)

  const { data: annex, isPending } = useQuery({
    queryKey: ['explainability', engagementId, findingId],
    queryFn: () => getExplainability(engagementId, findingId),
    refetchInterval: sharpening ? 2000 : false,
  })

  const sharpen = useMutation({
    mutationFn: () => sharpenExplainability(engagementId, findingId),
    onSuccess: () => { setConfirmOpen(false); setPrevSharpenedAt(annex?.sharpened_at || null); setSharpening(true) },
  })

  // Stop polling once a NEW sharpened timestamp lands (handles re-sharpen too).
  useEffect(() => {
    if (sharpening && annex?.sharpened_at && annex.sharpened_at !== prevSharpenedAt) {
      setSharpening(false)
      showToast('Annex sharpened by AI')
    }
  }, [sharpening, annex?.sharpened_at, prevSharpenedAt, showToast])

  if (isPending || !annex) {
    return <div className="flex items-center gap-2 py-4 text-sm text-fg-muted"><Loader2 size={14} className="animate-spin" /> Building annex…</div>
  }

  const s = annex.strength || { score: 0, label: '', factors: [] }

  return (
    <div className="mt-3 rounded-xl border border-brand/20 bg-brand-faint/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-caption text-brand">
            <ShieldCheck size={13} /> {annex.reference}
          </div>
          {annex.grounding_trail?.length > 0 && (
            <div className="mt-2">
              <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-fg-subtle">Grounding trail</div>
              <GroundingTrail trail={annex.grounding_trail} />
            </div>
          )}
        </div>
        <div className="shrink-0 text-center">
          <DefensibilityMeter score={s.score} label={s.label} />
          <div className="mt-0.5 max-w-[110px] text-[10px] leading-tight text-fg-subtle">
            Grounding strength — how much traceable support exists, not whether the finding is correct.
          </div>
        </div>
      </div>

      <ol className="mt-4 space-y-3">
        {annex.questions.map((q) => {
          const sg = SIGN[q.sign] || SIGN.info
          const SIcon = sg.Icon
          return (
            <li key={q.n} className="flex gap-2.5">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-3 text-[11px] font-bold text-fg-muted">{q.n}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-fg">
                  <SIcon size={13} className={sg.cls} /> {q.q}
                </div>
                <p className="mt-0.5 text-sm text-fg-muted">{q.answer}</p>
                {q.grounding?.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {q.grounding.map((g, i) => <GroundingChip key={i} kind={g.kind} label={g.label} />)}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      {s.factors?.length > 0 && (
        <div className="mt-4 border-t border-brand/15 pt-3">
          <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-fg-subtle">What supports the strength score</div>
          <div className="flex flex-wrap gap-1.5">
            {s.factors.map((f) => (
              <span
                key={f.key}
                title={`Weight ${f.weight}`}
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                  f.present ? 'text-sev-low bg-sev-low/10 ring-sev-low/25'
                            : 'text-fg-subtle bg-surface-2 ring-line'}`}
              >
                {f.present ? <Check size={11} /> : <Minus size={11} />} {f.label}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          onClick={() => setConfirmOpen(true)}
          disabled={sharpening}
          className="inline-flex items-center gap-1.5 rounded-lg border border-brand/30 px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
        >
          {sharpening ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {sharpening ? 'Sharpening…' : 'Sharpen with AI'}
        </button>
        {annex.sharpened_at && (
          <span className="text-[11px] text-fg-subtle">
            AI-sharpened{annex.sharpen_stale ? ' · may lag recent edits' : ''}
          </span>
        )}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => sharpen.mutate()}
        title="Sharpen the annex with AI?"
        description="Rewrites the five answers into crisper language. It uses AI budget and adds no new facts or figures — only rephrases the deterministic annex."
        confirmLabel="Sharpen — uses AI"
        loading={sharpen.isPending}
      />
    </div>
  )
}

export default function ExplainabilityAnnex({ engagementId, findingId }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-lg px-1 py-1 text-left text-sm font-medium text-fg transition hover:text-brand"
      >
        <ScrollText size={15} className="text-brand" />
        Explainability annex
        <span className="rounded-full bg-brand-subtle px-1.5 py-0.5 text-[10px] font-semibold text-brand">EU AI Act 13/14</span>
        <ChevronRight size={15} className={`ml-auto text-fg-subtle transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && <AnnexBody engagementId={engagementId} findingId={findingId} />}
    </div>
  )
}
