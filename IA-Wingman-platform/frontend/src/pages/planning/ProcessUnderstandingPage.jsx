import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ChevronDown, ChevronUp, RotateCcw, Check, X, Loader2, Sparkles } from 'lucide-react'
import {
  getProcessNotes,
  analyseProcessNotes,
  approveReasoning,
  patchProcessItem,
  acceptProcessItems,
} from '../../api/planning'
import { useStore } from '../../store/useStore'
import DocumentsUpload from '../../components/planning/DocumentsUpload'

const POLL_INTERVAL = 2500

function StatusBadge({ source }) {
  const cls = source === 'from_docs'
    ? 'bg-blue-50 text-blue-700'
    : 'bg-purple-50 text-purple-700'
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}>
      {source === 'from_docs' ? 'From sources' : 'Best practice'}
    </span>
  )
}

function ConfBadge({ confidence }) {
  const cls = confidence === 'high' ? 'bg-sev-low/10 text-sev-low'
    : confidence === 'medium' ? 'bg-sev-med/10 text-sev-med'
    : 'bg-surface-3 text-fg-muted'
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}>
      {confidence}
    </span>
  )
}

// ── State A — Setup ──────────────────────────────────────────────
function StateA({ onRun, isRunning }) {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-dashed border-line-strong bg-surface-3 p-6 text-center">
        <p className="text-sm text-fg-muted">
          The AI will read your uploaded documents and map the in-scope processes
          with step-by-step reasoning.
        </p>
        <p className="mt-1 text-xs text-fg-subtle">
          Documents uploaded in Topic Intelligence are available here automatically.
        </p>
      </div>
      <button
        onClick={onRun}
        disabled={isRunning}
        className="flex items-center gap-2 rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover disabled:opacity-60"
      >
        <Sparkles size={16} />
        {isRunning ? 'Starting analysis…' : 'Run Process Analysis'}
      </button>
    </div>
  )
}

// ── State B — Reasoning ──────────────────────────────────────────
function StateB({ pnData, onApprove, isApproving }) {
  const status = pnData?.status
  const reasoning = pnData?.reasoning

  const [editedReasoning, setEditedReasoning] = useState('')
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    if (reasoning?.approved_text) {
      setEditedReasoning(reasoning.approved_text)
    } else if (reasoning && status === 'reasoning_ready') {
      // Build display text from the JSON structure
      const r = reasoning
      const parts = []
      if (r.step1_understanding) parts.push(`Step 1 — Understanding the audit\n${r.step1_understanding}`)
      if (r.step2_sources?.length) {
        parts.push(`Step 2 — Sources reviewed (${r.step2_sources.length})\n${r.step2_sources.map(s => `• ${s.filename} — ${s.relevance}`).join('\n')}`)
      }
      if (r.step3_proposed_processes?.length) {
        parts.push(`Step 3 — Proposed in-scope processes (${r.step3_proposed_processes.length})\n${r.step3_proposed_processes.map(p => `• ${p.name} — ${p.rationale}`).join('\n')}`)
      }
      if (r.step3_excluded?.length) {
        parts.push(`Excluded\n${r.step3_excluded.map(p => `• [Excluded] ${p.name} — ${p.reason}`).join('\n')}`)
      }
      if (r.conclusion) parts.push(`Conclusion\n${r.conclusion}`)
      setEditedReasoning(parts.join('\n\n'))
    }
  }, [reasoning, status])

  const isWorking = status === 'reasoning' || status === 'generating'

  return (
    <div className="space-y-4">
      <div className="border border-line rounded-xl bg-surface">
        <button
          className="flex w-full items-center justify-between px-5 py-4"
          onClick={() => setExpanded(!expanded)}
        >
          <span className="text-sm font-semibold text-fg">Agent's Reasoning</span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {expanded && (
          <div className="border-t border-line px-5 pb-5">
            {isWorking ? (
              <div className="flex items-center gap-2 py-4 text-sm text-fg-muted">
                <Loader2 size={16} className="animate-spin text-brand" />
                {status === 'reasoning' ? 'Analysing processes… typically 30–60 seconds.' : 'Generating proposals…'}
              </div>
            ) : status === 'reasoning_ready' ? (
              <div className="mt-3">
                <textarea
                  className="w-full rounded-lg border border-line p-3 text-sm text-fg focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                  rows={14}
                  value={editedReasoning}
                  onChange={(e) => setEditedReasoning(e.target.value)}
                />
                <p className="mt-1 text-xs text-fg-subtle">You can edit the reasoning before approving.</p>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {status === 'reasoning_ready' && (
        <div className="flex gap-3 rounded-xl bg-brand-subtle px-5 py-4">
          <button
            onClick={() => onApprove(editedReasoning)}
            disabled={isApproving}
            className="flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-hover disabled:opacity-60"
          >
            <Check size={15} />
            {isApproving ? 'Generating proposals…' : 'I agree — show me the proposals'}
          </button>
          <button
            onClick={() => onApprove(null)}
            className="flex items-center gap-2 rounded-lg border border-line bg-surface px-4 py-2 text-sm font-medium text-fg-muted hover:bg-surface-3"
          >
            <X size={15} />
            Discard and start over
          </button>
        </div>
      )}
    </div>
  )
}

// ── State C — Proposals ──────────────────────────────────────────
function StateC({ pnData, engagementId, onAccept, isAccepting }) {
  const items = pnData?.process_items || []
  const [localItems, setLocalItems] = useState(items)
  const [expanded, setExpanded] = useState({})
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  useEffect(() => {
    setLocalItems(items)
  }, [pnData])

  const patchMutation = useMutation({
    mutationFn: ({ itemId, payload }) => patchProcessItem(engagementId, itemId, payload),
    onSuccess: (data) => {
      qc.setQueryData(['process-notes', engagementId], data)
    },
  })

  const toggle = (itemId) => {
    const updated = localItems.map((it) =>
      it.id === itemId ? { ...it, is_included: !it.is_included } : it
    )
    setLocalItems(updated)
    const item = updated.find((it) => it.id === itemId)
    patchMutation.mutate({ itemId, payload: { is_included: item.is_included } })
  }

  const included = localItems.filter((it) => it.is_included !== false)

  return (
    <div className="space-y-4">
      <p className="text-sm text-fg-muted">
        <strong>{localItems.length}</strong> processes proposed.{' '}
        <span className="text-fg-subtle">From sources = grounded in uploaded documents. Best practice = from audit knowledge.</span>
      </p>

      {localItems.map((item) => (
        <div
          key={item.id}
          className={`rounded-lg border border-line bg-surface transition-opacity ${item.is_included === false ? 'opacity-50' : ''}`}
        >
          <div
            className="flex cursor-pointer items-start gap-3 px-5 py-4"
            onClick={() => setExpanded((e) => ({ ...e, [item.id]: !e[item.id] }))}
          >
            <input
              type="checkbox"
              checked={item.is_included !== false}
              onChange={() => toggle(item.id)}
              onClick={(e) => e.stopPropagation()}
              className="mt-1 h-4 w-4 rounded border-line-strong text-brand"
            />
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-fg text-sm">{item.name}</span>
                <StatusBadge source={item.source} />
                <ConfBadge confidence={item.confidence} />
              </div>
              <p className="mt-1 text-xs text-fg-muted line-clamp-2">{item.description}</p>
            </div>
            <span className="text-fg-subtle text-xs ml-2 mt-1">
              {item.activities?.length || 0} activities
              {expanded[item.id] ? <ChevronUp size={14} className="inline ml-1" /> : <ChevronDown size={14} className="inline ml-1" />}
            </span>
          </div>

          {expanded[item.id] && (
            <div className="border-t border-line px-5 pb-4 pt-3">
              <p className="mb-3 text-xs text-fg-muted">{item.description}</p>
              {item.activities?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Activities</p>
                  {item.activities.map((act) => (
                    <div key={act.id} className="flex gap-2 rounded-lg bg-surface-3 px-3 py-2">
                      <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-brand" />
                      <div>
                        <p className="text-xs font-medium text-fg">{act.name}</p>
                        <p className="text-xs text-fg-muted">{act.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      <div className="rounded-xl bg-brand-subtle px-5 py-4">
        <button
          onClick={() => onAccept(localItems)}
          disabled={isAccepting || included.length === 0}
          className="flex items-center gap-2 rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover disabled:opacity-60"
        >
          <Check size={15} />
          {isAccepting ? 'Saving…' : `Accept ${included.length} process${included.length !== 1 ? 'es' : ''} & cascade to Scope`}
        </button>
        <p className="mt-2 text-xs text-fg-muted">
          Included processes are added to Scope &amp; Objectives for review.
        </p>
      </div>
    </div>
  )
}

// ── State D — Agreed ─────────────────────────────────────────────
function StateD({ pnData, onRunAgain }) {
  const items = pnData?.process_items || []
  const obs = pnData?.preliminary_observations || []
  const included = items.filter((it) => it.is_included !== false)

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-sev-low/10 px-5 py-4 text-sm text-sev-low">
        <p className="flex items-center gap-1.5 font-semibold"><Check size={15} /> Process Understanding saved</p>
        <ul className="mt-2 space-y-1 text-xs">
          <li>Processes created: <strong>{included.length}</strong></li>
          <li>Activities created: <strong>{included.reduce((s, it) => s + (it.activities?.length || 0), 0)}</strong></li>
          <li>Preliminary observations: <strong>{obs.length}</strong> (cascaded to Scope &amp; Objectives)</li>
        </ul>
      </div>

      <div className="border border-line rounded-xl bg-surface p-5 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">Processes accepted</p>
        {included.map((item) => (
          <div key={item.id} className="flex items-start gap-2">
            <Check size={14} className="mt-0.5 text-sev-low flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-fg">{item.name}</p>
              <p className="text-xs text-fg-muted">{item.activities?.length || 0} activities</p>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onRunAgain}
        className="flex items-center gap-2 text-sm text-brand hover:underline"
      >
        <RotateCcw size={14} /> Run again
      </button>
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────
export default function ProcessUnderstandingPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const { data: pnData } = useQuery({
    queryKey: ['process-notes', id],
    queryFn: () => getProcessNotes(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'reasoning' || status === 'generating' ? POLL_INTERVAL : false
    },
  })

  const status = pnData?.status || 'not_started'

  const runMutation = useMutation({
    mutationFn: () => analyseProcessNotes(id),
    onSuccess: (data) => {
      qc.setQueryData(['process-notes', id], data)
    },
    onError: () => showToast('Could not start analysis', 'error'),
  })

  const approveMutation = useMutation({
    mutationFn: (reasoning) =>
      reasoning ? approveReasoning(id, reasoning) : analyseProcessNotes(id),
    onSuccess: (data) => {
      qc.setQueryData(['process-notes', id], data)
    },
    onError: () => showToast('Could not approve reasoning', 'error'),
  })

  const acceptMutation = useMutation({
    mutationFn: (items) => acceptProcessItems(id, items),
    onSuccess: (data) => {
      qc.setQueryData(['process-notes', id], data)
      qc.invalidateQueries({ queryKey: ['engagement', id] })
      showToast('Process understanding saved')
    },
    onError: () => showToast('Could not save', 'error'),
  })

  const runAgain = () => {
    runMutation.mutate()
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
      <button
        onClick={() => navigate(`/engagements/${id}/planning`)}
        className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
      >
        <ArrowLeft size={16} /> Back to planning
      </button>

      <div className="mb-6">
        <h1 className="text-h1 text-fg">Process Understanding</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Document the end-to-end processes under audit — with AI-powered analysis.
        </p>
      </div>

      <div className="mb-6">
        <DocumentsUpload engagementId={id} title="Process documents" />
      </div>

      {(status === 'not_started') && (
        <StateA onRun={() => runMutation.mutate()} isRunning={runMutation.isPending} />
      )}

      {(status === 'reasoning' || status === 'reasoning_ready' || status === 'generating') && (
        <StateB
          pnData={pnData}
          onApprove={(reasoning) => approveMutation.mutate(reasoning)}
          isApproving={approveMutation.isPending}
        />
      )}

      {status === 'draft_ready' && (
        <StateC
          pnData={pnData}
          engagementId={id}
          onAccept={(items) => acceptMutation.mutate(items)}
          isAccepting={acceptMutation.isPending}
        />
      )}

      {status === 'agreed' && (
        <StateD pnData={pnData} onRunAgain={runAgain} />
      )}
    </div>
  )
}
