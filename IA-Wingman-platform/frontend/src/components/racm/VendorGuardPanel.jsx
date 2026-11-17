import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ShieldQuestion, Sparkles, Loader2, RefreshCw, Download, AlertTriangle, Check, ArrowUpRight } from 'lucide-react'
import { getVendorGuard, runVendorGuard, downloadVendorGuardReport } from '../../api/racm'
import { listDocuments } from '../../api/agents'
import { Card } from '../ui/Card'
import ConfirmDialog from '../ui/ConfirmDialog'
import { useStore } from '../../store/useStore'
import Tooltip from '../ui/Tooltip'

// Vendor Guard: opt-in AI third-party risk assessment against 8 curated
// frameworks. Applicability, the RAG scorecard and the gap→risk mapping are
// deterministic server-side; the specialist assessments + memo are the paid
// steps, gated behind the cost dialog. Critical/High gaps are proposed into the
// spine (accept/dismiss).

// See GovernanceAssessorPanel: the count was never coverage.
const COVERAGE_HINT = 'What this agent actually read. Long documents are passed in as an extract, so a requirement can be absent from the extract without being absent from the document.'

const RAG_TONE = {
  Red: 'bg-sev-high/10 text-sev-high',
  Amber: 'bg-sev-med/10 text-sev-med',
  Green: 'bg-sev-low/10 text-sev-low',
}
const SEV_TONE = {
  Critical: 'bg-sev-high/10 text-sev-high',
  High: 'bg-sev-med/10 text-sev-med',
  Medium: 'bg-sev-med/10 text-sev-med',
  Low: 'bg-surface-3 text-fg-muted',
  Info: 'bg-surface-3 text-fg-subtle',
}

export default function VendorGuardPanel({ engagementId }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const showToast = useStore((s) => s.showToast)
  const [vendorName, setVendorName] = useState('')
  const [isAi, setIsAi] = useState(false)
  const [isGov, setIsGov] = useState(false)
  const [docIds, setDocIds] = useState([])
  const [draftMemo, setDraftMemo] = useState(true)
  const [proposeSpine, setProposeSpine] = useState(true)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const { data } = useQuery({
    queryKey: ['vendor-guard', engagementId],
    queryFn: () => getVendorGuard(engagementId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'running' ? 2500 : false
    },
  })
  const { data: documents } = useQuery({ queryKey: ['documents', engagementId], queryFn: () => listDocuments(engagementId) })
  const readyDocs = (documents || []).filter((d) => d.upload_status === 'ready')

  const run = useMutation({
    mutationFn: () => runVendorGuard(engagementId, {
      vendor_name: vendorName, is_ai_system: isAi, is_dutch_government: isGov,
      document_ids: docIds, draft_memo: draftMemo, propose_to_spine: proposeSpine,
    }),
    onSuccess: () => { setConfirmOpen(false); qc.invalidateQueries({ queryKey: ['vendor-guard', engagementId] }) },
  })

  const status = data?.status
  useEffect(() => {
    if (status === 'complete') {
      qc.invalidateQueries({ queryKey: ['racm', engagementId] })
      showToast('Vendor assessment complete')
    }
  }, [status, engagementId, qc, showToast])

  const busy = status === 'pending' || status === 'running' || run.isPending
  const result = data?.result
  const noDocs = result?.error_kind === 'no_documents'
  const scorecard = result?.scorecard || {}
  const gaps = result?.gap_register || []

  const toggleDoc = (id) => setDocIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
          <ShieldQuestion size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Vendor Guard · third-party risk</h3>
            <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[11px] font-semibold text-brand">AI</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            Assesses uploaded vendor documents against curated frameworks (ISO 27001, NIS2, CBW, DORA, and —
            when applicable — EU AI Act/ALTAI/EC Ethics and BIO2), producing a RAG scorecard and gap register.
            Critical/High gaps are proposed into the matrix for you to accept or dismiss.
          </p>
        </div>
      </div>

      {/* Inputs */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <input value={vendorName} onChange={(e) => setVendorName(e.target.value)}
          placeholder="Vendor name"
          className="rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg placeholder:text-fg-subtle" />
        <div className="flex items-center gap-4 text-sm text-fg-muted">
          <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={isAi} onChange={(e) => setIsAi(e.target.checked)} /> AI system</label>
          <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={isGov} onChange={(e) => setIsGov(e.target.checked)} /> Dutch government</label>
        </div>
      </div>

      <div className="mt-3">
        <div className="text-caption text-fg-subtle">Vendor documents ({docIds.length} selected)</div>
        {readyDocs.length === 0 ? (
          <p className="mt-1 text-caption text-fg-subtle">No uploaded documents yet — upload the vendor's evidence first (Topic Intelligence / Process pages).</p>
        ) : (
          <div className="mt-1 flex flex-wrap gap-2">
            {readyDocs.map((d) => (
              <button key={d.id} onClick={() => toggleDoc(d.id)}
                className={`rounded-lg border px-2.5 py-1 text-caption transition ${docIds.includes(d.id) ? 'border-brand bg-brand-subtle text-brand' : 'border-line text-fg-muted hover:border-brand/40'}`}>
                {docIds.includes(d.id) && <Check size={11} className="mr-1 inline" />}{d.original_filename}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-fg-muted">
        <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={draftMemo} onChange={(e) => setDraftMemo(e.target.checked)} /> Draft audit memo</label>
        <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={proposeSpine} onChange={(e) => setProposeSpine(e.target.checked)} /> Propose gaps into matrix</label>
        <button
          onClick={() => setConfirmOpen(true)}
          disabled={busy || readyDocs.length === 0}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : result ? <RefreshCw size={15} /> : <Sparkles size={15} />}
          {busy ? 'Assessing…' : result ? 'Re-run' : 'Run vendor assessment'}
        </button>
      </div>

      {status === 'failed' && (
        <div className="mt-4 rounded-lg bg-sev-high/10 px-3 py-2 text-sm text-sev-high">
          The assessment did not complete. You can run it again.
        </div>
      )}
      {noDocs && (
        <div className="mt-4 rounded-lg bg-sev-med/10 px-3 py-2 text-sm text-sev-med">
          {result.message}
        </div>
      )}

      {result && !noDocs && status === 'complete' && (
        <div className="mt-4 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-fg-subtle">
            <span className={`rounded-full px-2 py-0.5 font-medium ${RAG_TONE[result.overall_rag] || ''}`}>Overall: {result.overall_rag}</span>
            <Tooltip label={COVERAGE_HINT} width="18rem">
              <span className="cursor-help underline decoration-dotted underline-offset-2">
                {result.document_coverage?.sentence || `${result.documents_assessed} doc(s)`}
              </span>
            </Tooltip>
            <span>{result.total_findings} findings</span>
            {result.proposed_risk_count > 0 && (
              <button onClick={() => navigate(`/engagements/${engagementId}/racm`)}
                className="inline-flex items-center gap-1 font-medium text-brand hover:underline">
                {result.proposed_risk_count} gap(s) proposed into the matrix <ArrowUpRight size={12} />
              </button>
            )}
            <button onClick={() => downloadVendorGuardReport(engagementId)}
              className="ml-auto inline-flex items-center gap-1.5 text-brand hover:underline">
              <Download size={13} /> Download Word
            </button>
          </div>

          {/* Scorecard */}
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(scorecard).map(([fw, d]) => (
              <div key={fw} className="rounded-lg border border-line bg-surface-2 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${RAG_TONE[d.rag] || ''}`}>{d.rag}</span>
                  <span className="text-sm font-medium text-fg">{fw}</span>
                </div>
                <div className="mt-0.5 text-caption text-fg-subtle">{d.total} controls · {d.gaps} gaps · {d.critical + d.high} critical/high</div>
              </div>
            ))}
          </div>

          {/* Gap register */}
          <div className="mt-3 space-y-2">
            {gaps.filter((f) => f.status !== 'Compliant').slice(0, 20).map((f, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg bg-surface-2 px-3 py-2">
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${SEV_TONE[f.severity] || 'bg-surface-3 text-fg-muted'}`}>
                  {f.status === 'Gap' ? <AlertTriangle size={11} className="mr-1 inline" /> : null}{f.severity}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-fg">
                    <span className="font-medium">{f.framework} {f.control_id}</span> · {f.control_name}
                    <span className="ml-1 text-fg-subtle">({f.status})</span>
                  </div>
                  {f.evidence && <div className="mt-0.5 text-caption text-fg-muted">{f.evidence}</div>}
                  {f.recommendation && <div className="mt-0.5 text-caption italic text-fg-subtle">→ {f.recommendation}</div>}
                </div>
              </div>
            ))}
          </div>

          {result.memo && (
            <details className="mt-3 rounded-lg border border-line bg-surface-2 p-3">
              <summary className="cursor-pointer text-sm font-medium text-fg">Audit memo</summary>
              <pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-fg-muted">{result.memo}</pre>
            </details>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => run.mutate()}
        title="Run the vendor assessment?"
        description="This uses AI budget: one specialist assessment per applicable framework group (security + resilience always; AI trust and government baseline when flagged), plus an optional memo. Findings are advisory and any proposed risks are yours to accept or dismiss."
        confirmLabel="Run — uses AI"
        loading={run.isPending}
      />
    </Card>
  )
}
