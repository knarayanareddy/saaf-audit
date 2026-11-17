import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BarChart3, Sparkles, Loader2, RefreshCw, AlertTriangle, Check, ArrowUpRight } from 'lucide-react'
import { getDataAnalysis, runDataAnalysis } from '../../api/racm'
import { Card } from '../ui/Card'
import ConfirmDialog from '../ui/ConfirmDialog'
import { useStore } from '../../store/useStore'

// Data-Analysis / Anomaly agent. The analysis itself is deterministic and free —
// real full-population counts, no AI. Exceptions are proposed as tests in the
// spine. An opt-in "Explain with AI" step adds plain-language narration only.
export default function DataAnalysisPanel({ engagementId }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const showToast = useStore((s) => s.showToast)
  const [explainOpen, setExplainOpen] = useState(false)

  const { data } = useQuery({
    queryKey: ['data-analysis', engagementId],
    queryFn: () => getDataAnalysis(engagementId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'running' ? 2000 : false
    },
  })

  const run = useMutation({
    mutationFn: (narrate) => runDataAnalysis(engagementId, narrate),
    onSuccess: () => {
      setExplainOpen(false)
      qc.invalidateQueries({ queryKey: ['data-analysis', engagementId] })
    },
  })

  const status = data?.status
  useEffect(() => {
    if (status === 'complete') {
      qc.invalidateQueries({ queryKey: ['racm', engagementId] })
      showToast('Analysis complete — exceptions proposed into the matrix')
    }
  }, [status, engagementId, qc, showToast])

  const busy = status === 'pending' || status === 'running' || run.isPending
  const result = data?.result
  const checks = result?.checks || []

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
          <BarChart3 size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Data-Analysis / Anomaly agent</h3>
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            Runs full-population tests (duplicates, missing evidence, outliers, threshold gaming, segregation
            of duties) over the dataset. Every count is computed — no AI, no invented numbers. Exceptions are
            proposed as tests in the matrix.
          </p>
        </div>
        <button
          onClick={() => run.mutate(false)}
          disabled={busy}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : result ? <RefreshCw size={15} /> : <BarChart3 size={15} />}
          {busy ? 'Analysing…' : result ? 'Re-run' : 'Run analysis'}
        </button>
      </div>

      {status === 'failed' && (
        <div className="mt-4 rounded-lg bg-sev-high/10 px-3 py-2 text-sm text-sev-high">
          The analysis did not complete. You can run it again.
        </div>
      )}

      {result && status === 'complete' && (
        <div className="mt-4 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-fg-subtle">
            <span>{result.row_count ?? 0} records analysed</span>
            <span>{result.total_exceptions ?? 0} exceptions</span>
            <button onClick={() => navigate(`/engagements/${engagementId}/racm`)}
              className="inline-flex items-center gap-1 font-medium text-brand hover:underline">
              {result.proposed_test_count ?? 0} test(s) proposed into the matrix <ArrowUpRight size={12} />
            </button>
          </div>

          <div className="mt-3 space-y-2">
            {checks.map((c, i) => {
              const has = c.exceptions_count > 0
              return (
                <div key={i} className="flex items-start gap-2 rounded-lg bg-surface-2 px-3 py-2">
                  <span className={`mt-0.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${has ? 'bg-sev-med/10 text-sev-med' : 'bg-sev-low/10 text-sev-low'}`}>
                    {has ? <AlertTriangle size={11} /> : <Check size={11} />}
                    {c.exceptions_count}/{c.sample_size}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-fg">{c.title}</div>
                    <div className="mt-0.5 text-caption text-fg-muted">{c.description}</div>
                    {c.examples?.length > 0 && (
                      <div className="mt-0.5 text-caption text-fg-subtle">e.g. {c.examples.join(', ')}</div>
                    )}
                    {c.explanation && <div className="mt-1 text-caption italic text-fg-muted">{c.explanation}</div>}
                  </div>
                </div>
              )
            })}
          </div>

          <button
            onClick={() => setExplainOpen(true)}
            disabled={busy}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-brand/30 px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
          >
            <Sparkles size={14} /> Explain with AI
          </button>
        </div>
      )}

      <ConfirmDialog
        open={explainOpen}
        onClose={() => setExplainOpen(false)}
        onConfirm={() => run.mutate(true)}
        title="Add AI explanations?"
        description="This re-runs the same deterministic analysis and asks the AI to add a plain-language sentence per check. It uses AI budget; the figures never change."
        confirmLabel="Explain — uses AI"
        loading={run.isPending}
      />
    </Card>
  )
}
