import { useParams, useNavigate } from 'react-router-dom'
import { downloadFile } from '../../api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, Sparkles, Loader2, AlertTriangle, CheckCircle2, Send, ChevronRight, Check, X, Download } from 'lucide-react'
import {
  getANL, updateANL, draftANL, reviewANL, updateANLComment,
  submitHeadIA, headIAApprove, markANLSent,
} from '../../api/planning'
import { getEngagement } from '../../api/engagements'
import EditableText from '../../components/ui/EditableText'
import Button from '../../components/ui/Button'
import AIFieldHelper from '../../components/ui/AIFieldHelper'
import { useStore } from '../../store/useStore'

// ── Status helpers ─────────────────────────────────────────────────────────────
const STATUS_META = {
  not_started: { label: 'Not started', color: 'text-fg-subtle' },
  drafting: { label: 'Drafting…', color: 'text-sev-med' },
  draft_ready: { label: 'Draft ready', color: 'text-blue-600' },
  review_pending: { label: 'AI review in progress…', color: 'text-sev-med' },
  reviewed: { label: 'AI review complete', color: 'text-brand' },
  head_ia_review: { label: 'Awaiting Head IA review', color: 'text-violet-600' },
  approved: { label: 'Approved by Head IA', color: 'text-sev-low' },
  sent: { label: 'Sent to auditees', color: 'text-sev-low' },
}

const SECTIONS = [
  { key: 'background', label: 'Background' },
  { key: 'objectives', label: 'Objectives' },
  { key: 'scope_description', label: 'Scope' },
  { key: 'out_of_scope', label: 'Not in scope' },
  { key: 'approach', label: 'Approach' },
  { key: 'responsibility', label: 'Responsibility' },
]

const TIMING_FIELDS = [
  { key: 'timing_fieldwork_start', label: 'Fieldwork start' },
  { key: 'timing_fieldwork_end', label: 'Fieldwork end' },
  { key: 'timing_draft_report', label: 'Draft report by' },
  { key: 'timing_mgmt_response', label: 'Management response by' },
  { key: 'timing_final_report', label: 'Final report by' },
]

// ── Review comment card ────────────────────────────────────────────────────────
function ReviewComment({ comment, onAccept, onDismiss }) {
  const isMust = comment.severity === 'must_fix'
  const done = comment.is_accepted || comment.is_dismissed

  return (
    <div className={`rounded-lg border p-3 text-sm ${
      done ? 'border-line bg-surface-3 opacity-60' :
      isMust ? 'border-sev-high/25 bg-sev-high/10' : 'border-sev-med/25 bg-sev-med/10'
    }`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
          isMust ? 'bg-sev-high/10 text-sev-high' : 'bg-sev-med/10 text-sev-med'
        }`}>
          {isMust ? 'Must fix' : 'Suggestion'}
        </span>
        <span className="text-xs font-medium text-fg-muted capitalize">{comment.section?.replace(/_/g,' ')}</span>
        {comment.is_accepted && <span className="inline-flex items-center gap-0.5 text-[10px] text-sev-low font-medium"><Check size={10} /> Accepted</span>}
        {comment.is_dismissed && <span className="text-[10px] text-fg-subtle font-medium">Dismissed</span>}
      </div>
      <p className="text-fg text-sm">{comment.comment}</p>
      {!done && (
        <div className="mt-2 flex gap-2">
          <button onClick={onAccept} className="flex items-center gap-1 rounded bg-sev-low/100 px-2 py-1 text-xs text-white hover:bg-sev-low/100">
            <Check size={12}/> Accept
          </button>
          <button onClick={onDismiss} className="flex items-center gap-1 rounded border border-line bg-surface px-2 py-1 text-xs text-fg-muted hover:bg-surface-3">
            <X size={12}/> Dismiss
          </button>
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function ANLPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['anl', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  const { data: anl } = useQuery({
    queryKey: ['anl', id],
    queryFn: () => getANL(id),
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return (status === 'drafting' || status === 'review_pending') ? 3000 : false
    },
  })

  const patch = useMutation({ mutationFn: (p) => updateANL(id, p), onSuccess: invalidate })
  const draft = useMutation({ mutationFn: () => draftANL(id), onSuccess: () => { showToast('Draft started — usually takes 30–60 seconds'); invalidate() } })
  const review = useMutation({ mutationFn: () => reviewANL(id), onSuccess: () => { showToast('AI review started'); invalidate() } })
  const commentMut = useMutation({ mutationFn: ({ cid, p }) => updateANLComment(id, cid, p), onSuccess: invalidate })
  const submitHIA = useMutation({ mutationFn: () => submitHeadIA(id), onSuccess: () => { showToast('Submitted to Head IA'); invalidate() } })
  const approveHIA = useMutation({ mutationFn: () => headIAApprove(id), onSuccess: () => { showToast('Approved by Head IA'); invalidate() } })
  const markSent = useMutation({ mutationFn: () => markANLSent(id), onSuccess: () => { showToast('ANL marked as sent'); invalidate() } })

  const status = anl?.status || 'not_started'
  const statusMeta = STATUS_META[status] || STATUS_META.not_started
  const comments = anl?.review_comments || []
  const pendingMustFix = comments.filter((c) => c.severity === 'must_fix' && !c.is_accepted && !c.is_dismissed).length
  const isProcessing = status === 'drafting' || status === 'review_pending'

  const downloadWord = async () => {
    try {
      await downloadFile(`/planning/${id}/anl/export-word`, `ANL-${eng?.audit_code || eng?.name?.slice(0, 20) || 'draft'}.docx`)
    } catch {
      showToast('Export failed', 'error')
    }
  }

  const Back = () => (
    <button onClick={() => navigate(`/engagements/${id}/planning`)} className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand">
      <ArrowLeft size={16}/> Back to planning
    </button>
  )

  // ── Not started ──────────────────────────────────────────────────────────────
  if (status === 'not_started') {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
        <Back/>
        <h1 className="text-h1 text-fg">Audit Notification Letter</h1>
        <p className="mt-1 text-sm text-fg-muted">
          The ANL is sent to key audit contacts before fieldwork begins. The AI drafter uses your accepted
          Topic Intelligence memo, scope items, and frameworks to generate a complete draft.
        </p>
        <div className="border border-line mt-6 rounded-xl bg-surface p-6 text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-brand-subtle">
            <FileText size={24} className="text-brand"/>
          </div>
          <h2 className="mt-3 font-semibold text-fg">No ANL yet</h2>
          <p className="mt-2 text-sm text-fg-muted">
            {eng?.planning_progress?.topic_intelligence < 100
              ? 'Complete Topic Intelligence first — the drafter needs your accepted regulatory memo and scope items.'
              : 'Topic Intelligence is complete. Ready to draft the ANL.'}
          </p>
          <div className="mt-5">
            <Button onClick={() => draft.mutate()} disabled={draft.isPending}>
              <Sparkles size={16}/> Draft ANL with AI
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // ── Drafting or review in progress ───────────────────────────────────────────
  if (isProcessing) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
        <Back/>
        <h1 className="text-h1 text-fg">Audit Notification Letter</h1>
        <div className="border border-line mt-8 flex flex-col items-center gap-3 rounded-xl bg-surface p-8 text-center">
          <Loader2 size={32} className="animate-spin text-brand"/>
          <p className="font-medium text-fg">{statusMeta.label}</p>
          <p className="text-sm text-fg-subtle">
            {status === 'drafting' ? 'Generating all ANL sections from your planning data…' : 'The review agent is reading the draft…'}
          </p>
        </div>
      </div>
    )
  }

  // ── Sent ─────────────────────────────────────────────────────────────────────
  if (status === 'sent') {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
        <Back/>
        <h1 className="text-h1 text-fg">Audit Notification Letter</h1>
        <div className="mt-6 rounded-xl bg-sev-low/10 p-6 text-center">
          <Send size={28} className="mx-auto text-sev-low mb-2"/>
          <p className="font-semibold text-sev-low">ANL sent to auditees</p>
          <p className="text-sm text-sev-low mt-1">The audit notification letter has been distributed. Fieldwork may begin.</p>
        <div className="mt-4">
          <Button variant="secondary" onClick={downloadWord}><Download size={14}/> Download Word</Button>
        </div>
        </div>
        <ANLReadonlyView anl={anl}/>
      </div>
    )
  }

  // ── Draft ready + reviewed + head IA + approved ───────────────────────────────
  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
      <Back/>
      <div className="flex items-center justify-between">
        <h1 className="text-h1 text-fg">Audit Notification Letter</h1>
        <span className={`text-sm font-medium ${statusMeta.color}`}>{statusMeta.label}</span>
      </div>

      {/* ── Action bar ── */}
      <div className="mt-4 flex flex-wrap gap-2">
        {status === 'draft_ready' && (
          <>
            <Button variant="secondary" onClick={() => draft.mutate()} disabled={draft.isPending}>
              <Sparkles size={14}/> Re-draft
            </Button>
            <Button onClick={() => review.mutate()} disabled={review.isPending}>
              <Sparkles size={14}/> AI Review
            </Button>
          </>
        )}
        {status === 'reviewed' && (
          <>
            <div className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium ${pendingMustFix > 0 ? 'bg-sev-high/10 text-sev-high' : 'bg-sev-low/10 text-sev-low'}`}>
              {pendingMustFix > 0 ? <AlertTriangle size={14}/> : <CheckCircle2 size={14}/>}
              {pendingMustFix > 0 ? `${pendingMustFix} must-fix issues pending` : 'All must-fix issues resolved'}
            </div>
            <Button variant="secondary" onClick={() => review.mutate()} disabled={review.isPending}>
              <Sparkles size={14}/> Re-run review
            </Button>
            <Button onClick={() => submitHIA.mutate()} disabled={submitHIA.isPending || pendingMustFix > 0}>
              <ChevronRight size={14}/> Submit to Head IA
              {pendingMustFix > 0 && <span className="ml-1 text-xs opacity-60">(resolve issues first)</span>}
            </Button>
          </>
        )}
        {status === 'head_ia_review' && (
          <Button onClick={() => approveHIA.mutate()} disabled={approveHIA.isPending}>
            <CheckCircle2 size={14}/> Approve (Head IA)
          </Button>
        )}
        {status === 'approved' && (
          <Button onClick={() => markSent.mutate()} disabled={markSent.isPending}>
            <Send size={14}/> Mark as sent
          </Button>
        )}
        <Button variant="secondary" onClick={() => draft.mutate()} disabled={draft.isPending || ['head_ia_review','approved','sent'].includes(status)}>
          Re-draft from scratch
        </Button>
        {status !== 'not_started' && (
          <Button variant="ghost" onClick={downloadWord}>
            <Download size={14}/> Download Word
          </Button>
        )}
      </div>

      {/* ── Review comments ── */}
      {comments.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">
            AI review comments ({comments.filter(c => !c.is_dismissed).length} active)
          </h2>
          <div className="space-y-2">
            {comments.map((c) => (
              <ReviewComment
                key={c.id}
                comment={c}
                onAccept={() => commentMut.mutate({ cid: c.id, p: { is_accepted: true } })}
                onDismiss={() => commentMut.mutate({ cid: c.id, p: { is_dismissed: true } })}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── ANL sections ── */}
      <div className="mt-6 space-y-4">
        {SECTIONS.map(({ key, label }) => (
          <div key={key} className="border border-line rounded-xl bg-surface p-5">
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wide text-fg-muted">{label}</label>
              <AIFieldHelper
                fieldLabel={label}
                currentValue={anl[key] || ''}
                engagementId={id}
                onAccept={(v) => patch.mutate({ [key]: v })}
              />
            </div>
            <EditableText
              value={anl[key] || ''}
              onSave={(v) => patch.mutate({ [key]: v })}
              placeholder={`Click to edit ${label.toLowerCase()}…`}
            />
            {comments.some(c => c.section === key.replace('_description','').replace('scope_','scope') && c.severity === 'must_fix' && !c.is_accepted && !c.is_dismissed) && (
              <p className="mt-1 text-xs text-sev-high flex items-center gap-1"><AlertTriangle size={11}/> Has unresolved must-fix comment above</p>
            )}
          </div>
        ))}

        {/* Timing section */}
        <div className="border border-line rounded-xl bg-surface p-5">
          <label className="mb-3 block text-xs font-semibold uppercase tracking-wide text-fg-muted">Timing</label>
          <div className="space-y-2">
            {TIMING_FIELDS.map(({ key, label }) => (
              <div key={key} className="flex items-center gap-3">
                <span className="w-48 text-sm text-fg-muted">{label}</span>
                <EditableText
                  value={anl[key] || ''}
                  onSave={(v) => patch.mutate({ [key]: v })}
                  placeholder="TBD"
                  multiline={false}
                  className="flex-1"
                />
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-fg-subtle">
            Guideline: draft report 2 weeks after fieldwork · management response 2 weeks after draft · final report 1 week after response.
          </p>
        </div>
      </div>
    </div>
  )
}

function ANLReadonlyView({ anl }) {
  return (
    <div className="mt-6 space-y-4">
      {SECTIONS.map(({ key, label }) => (
        anl[key] ? (
          <div key={key} className="border border-line rounded-xl bg-surface p-5">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-fg-muted">{label}</div>
            <p className="text-sm text-fg whitespace-pre-wrap">{anl[key]}</p>
          </div>
        ) : null
      ))}
    </div>
  )
}
