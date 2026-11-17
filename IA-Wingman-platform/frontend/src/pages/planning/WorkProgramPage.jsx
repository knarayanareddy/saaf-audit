import { useParams, useNavigate } from 'react-router-dom'
import { downloadFile } from '../../api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Sparkles, Loader2, Check, Lock, Download,
  Plus, Trash2, ChevronDown, ChevronRight,
} from 'lucide-react'
import { useState } from 'react'
import {
  getWorkProgram, generateWorkProgram, patchWorkProgramRow,
  addWorkProgramRow, deleteWorkProgramRow, signOffWorkProgram, reopenWorkProgram,
} from '../../api/planning'
import Button from '../../components/ui/Button'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import { useStore } from '../../store/useStore'
import Tooltip from '../../components/ui/Tooltip'

const STATUS_COLORS = {
  not_started: 'bg-surface-3 text-fg-muted',
  in_progress: 'bg-sev-med/10 text-sev-med',
  complete: 'bg-sev-low/10 text-sev-low',
}

const STATUS_OPTIONS = [
  { value: 'not_started', label: 'Not started' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'complete', label: 'Complete' },
]

function EditableCell({ value, onSave, multiline = false, className = '' }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  if (editing) {
    const props = {
      value: draft,
      onChange: (e) => setDraft(e.target.value),
      onBlur: () => { setEditing(false); if (draft !== value) onSave(draft) },
      autoFocus: true,
      className: 'w-full resize-none rounded border border-brand px-2 py-1 text-xs outline-none',
    }
    return multiline
      ? <textarea rows={3} {...props} />
      : <input type="text" {...props} />
  }

  return (
    <div
      onClick={() => { setDraft(value); setEditing(true) }}
      className={`cursor-pointer rounded px-1 py-0.5 text-xs text-fg hover:bg-surface-3 ${className}`}
    >
      {value || <span className="text-fg-subtle italic">Click to edit…</span>}
    </div>
  )
}

const PRIORITY_COLORS = {
  high: 'bg-sev-high/10 text-sev-high',
  medium: 'bg-sev-med/10 text-sev-med',
  low: 'bg-sev-low/10 text-sev-low',
}

// Backward-compatible: older rows stored a single `test_approach` string; treat it
// as one step so nothing is lost when the stepwise format rolled out.
function stepsOf(row) {
  if (Array.isArray(row.test_steps) && row.test_steps.length) return row.test_steps
  return row.test_approach ? [row.test_approach] : []
}

function TestStepsCell({ row, onPatch, locked }) {
  const steps = stepsOf(row)
  const save = (next) => onPatch(row.id, { test_steps: next })
  if (locked) {
    return steps.length
      ? <ol className="list-decimal space-y-0.5 pl-4 text-xs text-fg">{steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
      : <span className="text-xs text-fg-subtle">—</span>
  }
  return (
    <div className="space-y-1">
      {steps.map((s, i) => (
        <div key={i} className="flex items-start gap-1">
          <span className="mt-1 text-[10px] tabular-nums text-fg-subtle">{i + 1}.</span>
          <EditableCell
            value={s}
            multiline
            onSave={(v) => { const next = [...steps]; if (v.trim()) next[i] = v; else next.splice(i, 1); save(next) }}
            className="flex-1"
          />
        </div>
      ))}
      <button onClick={() => save([...steps, 'New test step'])} className="ml-4 flex items-center gap-1 text-[11px] text-brand hover:underline">
        <Plus size={11} /> Add step
      </button>
    </div>
  )
}

function PriorityCell({ row, onPatch, locked }) {
  const p = row.priority || 'medium'
  if (locked) {
    return <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${PRIORITY_COLORS[p] || ''}`}>{p}</span>
  }
  return (
    <select
      value={p}
      onChange={(e) => onPatch(row.id, { priority: e.target.value })}
      className={`rounded border border-line px-1.5 py-0.5 text-[11px] font-medium uppercase outline-none focus:border-brand ${PRIORITY_COLORS[p] || ''}`}
    >
      {['high', 'medium', 'low'].map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

function WPRow({ row, onPatch, onDelete, locked }) {

  return (
    <tr className="border-b border-line hover:bg-surface-3/50">
      <td className="px-3 py-2 text-xs text-fg-subtle w-8">{row.id?.split('_')[1] || ''}</td>
      <td className="px-3 py-2 min-w-[120px]">
        {locked
          ? <span className="text-xs text-fg">{row.process}</span>
          : <EditableCell value={row.process} onSave={(v) => onPatch(row.id, { process: v })} />}
      </td>
      <td className="px-3 py-2 min-w-[120px]">
        {locked
          ? <span className="text-xs text-fg">{row.activity}</span>
          : <EditableCell value={row.activity} onSave={(v) => onPatch(row.id, { activity: v })} />}
      </td>
      <td className="px-3 py-2 min-w-[180px]">
        {locked
          ? <span className="text-xs text-fg">{row.risk_description}</span>
          : <EditableCell value={row.risk_description} multiline onSave={(v) => onPatch(row.id, { risk_description: v })} />}
      </td>
      <td className="px-3 py-2 min-w-[180px]">
        {locked
          ? <span className="text-xs text-fg">{row.control_objective}</span>
          : <EditableCell value={row.control_objective} multiline onSave={(v) => onPatch(row.id, { control_objective: v })} />}
      </td>
      <td className="px-3 py-2 min-w-[190px] align-top">
        <TestStepsCell row={row} onPatch={onPatch} locked={locked} />
      </td>
      <td className="px-3 py-2 w-[90px] align-top">
        <PriorityCell row={row} onPatch={onPatch} locked={locked} />
      </td>
      <td className="px-3 py-2 w-[90px] align-top">
        {locked
          ? <span className="text-xs text-fg">{row.responsibility}</span>
          : <EditableCell value={row.responsibility} onSave={(v) => onPatch(row.id, { responsibility: v })} />}
      </td>
      <td className="px-3 py-2 w-[110px]">
        {locked
          ? <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${STATUS_COLORS[row.status] || STATUS_COLORS.not_started}`}>
              {row.status?.replace('_', ' ')}
            </span>
          : <select
              value={row.status}
              onChange={(e) => onPatch(row.id, { status: e.target.value })}
              className="rounded border border-line px-1.5 py-0.5 text-[11px] outline-none focus:border-brand"
            >
              {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
        }
      </td>
      {!locked && (
        <td className="px-3 py-2 w-8">
          <Tooltip label="Delete this step" side="left">
            <button onClick={() => onDelete(row.id)} aria-label="Delete this step" className="text-fg-subtle hover:text-sev-high">
              <Trash2 size={13} />
            </button>
          </Tooltip>
        </td>
      )}
    </tr>
  )
}

export default function WorkProgramPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [signOffConfirm, setSignOffConfirm] = useState(false)

  const { data: wp } = useQuery({
    queryKey: ['work-program', id],
    queryFn: () => getWorkProgram(id),
    refetchInterval: (q) => (q.state.data?.status === 'generating' ? 3000 : false),
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['work-program', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  const generateMutation = useMutation({
    mutationFn: () => generateWorkProgram(id),
    onSuccess: invalidate,
    onError: (e) => showToast(e.response?.data?.detail || 'Generation failed', 'error'),
  })

  const patchMutation = useMutation({
    mutationFn: ({ rowId, payload }) => patchWorkProgramRow(id, rowId, payload),
    onSuccess: (data) => qc.setQueryData(['work-program', id], data),
  })

  const addMutation = useMutation({
    mutationFn: () => addWorkProgramRow(id, {
      process: 'New process', activity: '', risk_description: '', control_objective: '',
      test_steps: [], priority: 'medium', responsibility: 'IA team',
    }),
    onSuccess: (data) => qc.setQueryData(['work-program', id], data),
  })

  const deleteMutation = useMutation({
    mutationFn: (rowId) => deleteWorkProgramRow(id, rowId),
    onSuccess: (data) => qc.setQueryData(['work-program', id], data),
  })

  const signOffMutation = useMutation({
    mutationFn: () => signOffWorkProgram(id),
    onSuccess: (data) => { qc.setQueryData(['work-program', id], data); showToast('Work program signed off') },
    onError: () => showToast('Could not sign off', 'error'),
  })

  const reopenMutation = useMutation({
    mutationFn: () => reopenWorkProgram(id),
    onSuccess: (data) => { qc.setQueryData(['work-program', id], data); showToast('Work program reopened') },
  })

  const downloadXlsx = async () => {
    try {
      await downloadFile(`/planning/${id}/work-program/export-xlsx`, 'WorkProgram.xlsx')
    } catch {
      showToast('Export failed', 'error')
    }
  }

  const status = wp?.status || 'draft'
  const rows = wp?.rows || []
  const locked = status === 'signed_off'
  const isGenerating = status === 'generating'

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
      <button
        onClick={() => navigate(`/engagements/${id}/planning`)}
        className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
      >
        <ArrowLeft size={16} /> Back to planning
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-h1 text-fg">Work Program</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Planning matrix — generated from your accepted processes, requirements, and risks.
            Head IA sign-off unlocks Fieldwork.
          </p>
        </div>
        <div className="flex gap-2">
          {locked && (
            <div className="flex items-center gap-1.5 rounded-lg bg-sev-low/10 px-3 py-2 text-sm text-sev-low">
              <Lock size={13} /> Signed off
              {wp?.signed_off_at && (
                <span className="ml-1 text-xs text-sev-low">
                  {new Date(wp.signed_off_at).toLocaleDateString('nl-NL')}
                </span>
              )}
            </div>
          )}
          {locked && (
            <Button variant="ghost" onClick={() => reopenMutation.mutate()}>
              Reopen
            </Button>
          )}
          {rows.length > 0 && (
            <Button variant="ghost" onClick={downloadXlsx}>
              <Download size={14} /> Export Excel
            </Button>
          )}
          {!locked && !isGenerating && (
            <Button
              variant={rows.length > 0 ? 'secondary' : 'primary'}
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              <Sparkles size={14} />
              {rows.length > 0 ? 'Regenerate' : 'Generate from scope'}
            </Button>
          )}
          {!locked && rows.length > 0 && (
            <Button onClick={() => setSignOffConfirm(true)} disabled={signOffMutation.isPending}>
              <Check size={14} /> Sign off → Fieldwork
            </Button>
          )}
        </div>
      </div>

      {isGenerating && (
        <div className="border border-line mt-8 flex items-center gap-3 rounded-xl bg-surface p-6 text-sm text-fg-muted">
          <Loader2 size={20} className="animate-spin text-brand" />
          Generating work program from accepted processes, requirements, and risks… typically 20–40 seconds.
        </div>
      )}

      {!isGenerating && rows.length === 0 && (
        <div className="border border-line mt-8 rounded-xl bg-surface p-8 text-center">
          <Sparkles size={32} className="mx-auto mb-3 text-brand-light" />
          <p className="text-sm text-fg-muted">
            Click "Generate from scope" to auto-populate the work program from your accepted
            processes (Process Understanding), control requirements (Regulatory Requirements),
            and risks (Background Risk Assessment).
          </p>
          <p className="mt-2 text-xs text-fg-subtle">
            You can also add rows manually after generating.
          </p>
        </div>
      )}

      {!isGenerating && rows.length > 0 && (
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm text-fg-muted">{rows.length} rows</span>
            {!locked && (
              <button
                onClick={() => addMutation.mutate()}
                className="flex items-center gap-1 text-xs text-brand hover:underline"
              >
                <Plus size={12} /> Add row
              </button>
            )}
          </div>

          <div className="overflow-x-auto rounded-xl border border-line bg-surface">
            <table className="w-full min-w-[900px]">
              <thead>
                <tr className="border-b border-line bg-surface-3 text-left">
                  {['#', 'Process', 'Activity', 'Risk description', 'Control objective',
                    'Test steps', 'Priority', 'Responsibility', 'Status', ...(locked ? [] : [''])].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <WPRow
                    key={row.id}
                    row={row}
                    locked={locked}
                    onPatch={(rowId, payload) => patchMutation.mutate({ rowId, payload })}
                    onDelete={(rowId) => deleteMutation.mutate(rowId)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {!locked && (
            <p className="mt-3 text-xs text-fg-subtle text-center">
              Click any cell to edit. All changes save automatically.
            </p>
          )}
        </div>
      )}

      <ConfirmDialog
        open={signOffConfirm}
        onClose={() => setSignOffConfirm(false)}
        onConfirm={() => { setSignOffConfirm(false); signOffMutation.mutate() }}
        title="Sign off the work program?"
        description="This locks the work program for editing and unlocks the Fieldwork phase. You can reopen it later if needed."
        confirmLabel="Sign off"
        loading={signOffMutation.isPending}
      />
    </div>
  )
}
