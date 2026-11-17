import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ScanSearch, Sparkles, Check, AlertTriangle, TriangleAlert, Loader2, RefreshCw, ArrowUpRight, FileText } from 'lucide-react'
import { getGovernanceAssessment, runGovernanceAssessment } from '../../api/racm'
import { Card } from '../ui/Card'
import ConfirmDialog from '../ui/ConfirmDialog'
import { useStore } from '../../store/useStore'
import Tooltip from '../ui/Tooltip'

// A file count reads like coverage and is not: an agent is given the opening
// characters of each document, not the document.
const COVERAGE_HINT = 'What this agent actually read. Long documents are passed in as an extract, so a requirement can be absent from the extract without being absent from the document.'

const COVERAGE = {
  covered: { tone: 'bg-sev-low/10 text-sev-low', icon: Check, label: 'covered' },
  partial: { tone: 'bg-sev-med/10 text-sev-med', icon: TriangleAlert, label: 'partial' },
  gap: { tone: 'bg-sev-high/10 text-sev-high', icon: AlertTriangle, label: 'gap' },
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
    // The assessment is one call per framework now, so the figures beside this
    // are the sum of all of them and the duration is the slowest — they run
    // together. Saying how many makes the totals readable as totals.
    run.calls > 1 ? `${run.calls} calls` : null,
    `${(run.duration_ms / 1000).toFixed(1)}s`,
    `${run.input_tokens?.toLocaleString()} in / ${run.output_tokens?.toLocaleString()} out`,
    run.thinking_tokens ? `${run.thinking_tokens.toLocaleString()} reasoning` : run.reasoned ? "reasoning not shown" : null,
    run.cached_tokens ? `${run.cached_tokens.toLocaleString()} cached` : null,
    money,
    run.repaired ? 'schema corrected on retry' : null,
  ].filter(Boolean)
  return <div className="mt-2 text-[11px] text-fg-subtle">{bits.join(' \u00b7 ')}</div>
}

// Where a judgement came from. The assessor now reads selected passages and is
// asked to cite them by id; each resolved id is the document, section and
// character range behind the claim. An id it invented resolves to nothing and is
// shown as such rather than quietly passing for provenance — the same rule the
// grounded validator applies to quotes.
function Citations({ cites }) {
  if (!cites || (!cites.cited?.length && !cites.unresolved?.length)) return null
  return (
    <div className="mt-1 flex flex-wrap items-center gap-1">
      {(cites.cited || []).map((c) => (
        <span
          key={c.cid}
          title={`${c.document} · ${c.section || 'no heading'} · characters ${c.char_start}–${c.char_end}`}
          className="inline-flex items-center gap-1 rounded-md bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted ring-1 ring-inset ring-line"
        >
          <FileText size={10} /> {c.section || c.document}
        </span>
      ))}
      {(cites.unresolved || []).map((cid) => (
        <span
          key={cid}
          title="The assessor cited a passage that does not exist — treat this judgement as unsupported"
          className="inline-flex items-center gap-1 rounded-md bg-sev-med/12 px-1.5 py-0.5 text-[11px] font-medium text-sev-med ring-1 ring-inset ring-sev-med/25"
        >
          <AlertTriangle size={10} /> {cid} not found
        </span>
      ))}
    </div>
  )
}

// The Governance-Document Assessor: opt-in AI that checks framework coverage and
// proposes the gaps as AI risks in the spine. Deterministic gap→risk mapping
// happens server-side; here we drive the run, poll status, and show coverage.
export default function GovernanceAssessorPanel({ engagementId }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const showToast = useStore((s) => s.showToast)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const { data } = useQuery({
    queryKey: ['governance-assessment', engagementId],
    queryFn: () => getGovernanceAssessment(engagementId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'running' ? 2500 : false
    },
  })

  const run = useMutation({
    mutationFn: () => runGovernanceAssessment(engagementId),
    onSuccess: () => {
      setConfirmOpen(false)
      qc.invalidateQueries({ queryKey: ['governance-assessment', engagementId] })
    },
  })

  // When a run finishes, the spine has new AI-proposed risks — refresh it.
  const status = data?.status
  useEffect(() => {
    if (status === 'complete') {
      qc.invalidateQueries({ queryKey: ['racm', engagementId] })
      showToast('Governance assessment complete — gaps proposed into the matrix')
    }
  }, [status, engagementId, qc, showToast])

  const busy = status === 'pending' || status === 'running' || run.isPending
  const result = data?.result
  const items = result?.items || []

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
          <ScanSearch size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Governance-Document Assessor</h3>
            <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[11px] font-semibold text-brand">AI</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            Checks whether your policies and controls cover the applicable laws and supervisory guidance,
            and proposes the coverage gaps as risks in the matrix — for you to accept or dismiss.
          </p>
        </div>
        <button
          onClick={() => setConfirmOpen(true)}
          disabled={busy}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : result ? <RefreshCw size={15} /> : <Sparkles size={15} />}
          {busy ? 'Assessing…' : result ? 'Re-assess' : 'Run assessor'}
        </button>
      </div>

      {status === 'failed' && (
        <div className="mt-4 rounded-lg bg-sev-high/10 px-3 py-2 text-sm text-sev-high">
          The assessment did not complete. You can run it again.
        </div>
      )}

      {result && status === 'complete' && (
        <div className="mt-4 border-t border-line pt-4">
          {result.summary && <p className="text-sm text-fg">{result.summary}</p>}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-caption text-fg-subtle">
            <Tooltip label={COVERAGE_HINT} width="18rem">
              <span className="cursor-help underline decoration-dotted underline-offset-2">
                {result.document_coverage?.sentence || `${result.documents_assessed ?? 0} document(s) assessed`}
              </span>
            </Tooltip>
            <button onClick={() => navigate(`/engagements/${engagementId}/racm`)}
              className="inline-flex items-center gap-1 font-medium text-brand hover:underline">
              {result.proposed_risk_count ?? 0} gap(s) proposed into the matrix <ArrowUpRight size={12} />
            </button>
          </div>

          <div className="mt-3 space-y-2">
            {items.map((it, i) => {
              const cov = COVERAGE[(it.coverage || '').toLowerCase()] || COVERAGE.covered
              const Icon = cov.icon
              return (
                <div key={i} className="flex items-start gap-2 rounded-lg bg-surface-2 px-3 py-2">
                  <span className={`mt-0.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${cov.tone}`}>
                    <Icon size={11} /> {cov.label}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-fg">
                      {it.requirement} {it.framework_ref && <span className="text-fg-subtle">· {it.framework_ref}</span>}
                    </div>
                    {it.evidence && <div className="mt-0.5 text-caption text-fg-muted">{it.evidence}</div>}
                    <Citations cites={it.citations} />
                  </div>
                </div>
              )
            })}
            {items.length === 0 && <div className="text-sm text-fg-subtle">No requirements were returned.</div>}
          </div>
          <RunReceipt run={result.run} />
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => run.mutate()}
        title="Run the Governance Assessor?"
        description="This uses AI budget. It reads your accepted frameworks, uploaded governance documents and the current control environment, then proposes coverage gaps as AI risks in the matrix (nothing is decided — you accept each one)."
        confirmLabel="Run — uses AI"
        loading={run.isPending}
      />
    </Card>
  )
}
