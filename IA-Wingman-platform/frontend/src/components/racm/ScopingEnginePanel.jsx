import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { LayoutList, Loader2, RefreshCw, Wand2, ArrowRight, Check } from 'lucide-react'
import { getScopingPreview, runScoping } from '../../api/racm'
import { Card } from '../ui/Card'
import { useStore } from '../../store/useStore'

// Planning & Scoping engine. Deterministic and free: it reads the completed
// planning modules (scope & objectives, key audit questions, topic intelligence,
// the background risk assessment) and proposes the top of the spine — objectives,
// risks and scope decisions — so fieldwork starts from a populated matrix.
export default function ScopingEnginePanel({ engagementId }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [result, setResult] = useState(null)

  const { data: preview, isPending } = useQuery({
    queryKey: ['scoping-preview', engagementId],
    queryFn: () => getScopingPreview(engagementId),
  })

  const run = useMutation({
    mutationFn: () => runScoping(engagementId),
    onSuccess: (data) => {
      setResult(data)
      qc.invalidateQueries({ queryKey: ['racm', engagementId] })
      qc.invalidateQueries({ queryKey: ['scoping-preview', engagementId] })
      const p = data.proposed
      showToast(
        data.total > 0
          ? `Front-loaded the spine: ${p.objectives} objective(s), ${p.risks} risk(s), ${p.scope_decisions} scope decision(s)`
          : 'Nothing new to propose — the spine already reflects your planning',
      )
    },
  })

  const would = preview?.would_propose
  const ready = preview?.ready
  const busy = run.isPending
  const sources = preview?.sources || {}

  const Line = ({ label, count, from }) => (
    <div className="flex items-baseline gap-2 rounded-lg bg-surface-2 px-3 py-2">
      <span className="min-w-[7rem] text-sm font-medium text-fg">{label}</span>
      <span className="text-sm tabular-nums text-brand">{count}</span>
      <span className="truncate text-caption text-fg-subtle">from {from}</span>
    </div>
  )

  return (
    <Card className="border-brand/20 bg-brand-faint p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-fg">
          <LayoutList size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Planning &amp; Scoping engine</h3>
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic · free</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            Turns the planning you have already done — scope &amp; objectives, key audit questions, topic
            intelligence and the background risk assessment — into the top of the matrix, so fieldwork starts
            from a populated, traceable spine instead of a blank one. Every item is proposed for you to accept.
          </p>
        </div>
        <button
          onClick={() => run.mutate()}
          disabled={busy || (preview && !ready)}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : result ? <RefreshCw size={15} /> : <Wand2 size={15} />}
          {busy ? 'Front-loading…' : result ? 'Re-run' : 'Front-load the spine'}
        </button>
      </div>

      {isPending && <div className="mt-4 h-14 animate-pulse rounded-lg bg-surface-3" />}

      {preview && !ready && !result && (
        <div className="mt-4 rounded-lg bg-surface-2 px-3 py-2.5 text-sm text-fg-muted">
          No planning data to cascade yet. Complete Scope &amp; Objectives, Topic Intelligence or the Background
          Risk Assessment and the engine will propose them here.
        </div>
      )}

      {preview && ready && !result && (
        <div className="mt-4 space-y-2 border-t border-brand/15 pt-4">
          <div className="text-caption font-medium uppercase tracking-wide text-fg-subtle">Ready to propose</div>
          <Line label="Objectives" count={would.objectives} from={sources.objectives?.from} />
          <Line label="Risks" count={would.risks} from={sources.risks?.from} />
          <Line label="Scope decisions" count={would.scope_decisions} from={sources.scope_decisions?.from} />
        </div>
      )}

      {result && (
        <div className="mt-4 border-t border-brand/15 pt-4">
          <div className="flex items-center gap-2 text-sm font-medium text-sev-low">
            <Check size={15} /> Front-loaded into the matrix
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-fg-muted">
            <span className="tabular-nums">{result.proposed.objectives} objective(s)</span>
            <span className="tabular-nums">{result.proposed.risks} risk(s)</span>
            <span className="tabular-nums">{result.proposed.scope_decisions} scope decision(s)</span>
          </div>
          <div className="mt-2 inline-flex items-center gap-1.5 text-caption text-fg-subtle">
            <ArrowRight size={13} /> New proposals appear in the lanes above, marked “AI”, awaiting your acceptance.
          </div>
        </div>
      )}
    </Card>
  )
}
