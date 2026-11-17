import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowUpRight, Check, X, Sparkles } from 'lucide-react'
import {
  getScope, updateScope, updateScopeItem, deleteScopeItem, updateQuestion, deleteQuestion,
} from '../../api/planning'
import { suggestObjective } from '../../api/ai'
import EditableText from '../../components/ui/EditableText'
import { Tag } from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import AIFieldHelper from '../../components/ui/AIFieldHelper'
import { useStore } from '../../store/useStore'
import { originOf, originPath } from '../../lib/scopeSources'

// Every item names the step that produced it. Six planning steps publish into
// this one list, and an auditor deciding on a proposal is entitled to know
// which of them is asking.
function OriginTag({ row, engagementId }) {
  const origin = originOf(row)
  if (!origin.label) return null
  const path = originPath(engagementId, row)
  const body = <>From {origin.label}</>
  if (!path) return <Tag className="bg-bg text-fg-subtle">{body}</Tag>
  return (
    <Link to={path} title={origin.ref ? `Produced by ${origin.ref}` : undefined}
      className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-medium text-violet-700 hover:bg-violet-200">
      {body}<ArrowUpRight size={11} />
    </Link>
  )
}

function ReviewRow({ accepted, row, engagementId, children, onAccept, onDismiss, onRemove }) {
  return (
    <div className={`rounded-lg border p-3 ${accepted ? 'border-sev-low/25 bg-sev-low/40' : 'border-line bg-surface'}`}>
      <div className="mb-1 flex flex-wrap items-center gap-1">
        {accepted ? <Tag className="bg-sev-low/10 text-sev-low">Accepted</Tag>
          : <Tag className="bg-sev-med/10 text-sev-med">Queued</Tag>}
        <OriginTag row={row} engagementId={engagementId} />
      </div>
      {children}
      <div className="mt-2 flex gap-2">
        {!accepted ? (
          <>
            <Button variant="success" onClick={onAccept} className="px-3 py-1 text-xs"><Check size={14} /> Accept</Button>
            <Button variant="danger" onClick={onDismiss} className="px-3 py-1 text-xs"><X size={14} /> Dismiss</Button>
          </>
        ) : (
          <Button variant="danger" onClick={onRemove} className="px-3 py-1 text-xs"><X size={14} /> Remove</Button>
        )}
      </div>
    </div>
  )
}

export default function ScopeObjectivesPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [generating, setGenerating] = useState(false)

  const { data: scope } = useQuery({ queryKey: ['scope', id], queryFn: () => getScope(id) })
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['scope', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  const saveObjective = useMutation({ mutationFn: (text) => updateScope(id, { overall_objective: text }), onSuccess: invalidate })

  const generateObjective = async () => {
    setGenerating(true)
    try {
      const { objective } = await suggestObjective(id)
      await saveObjective.mutateAsync(objective)
      showToast('Objective generated')
    } catch {
      showToast('Could not generate objective', 'error')
    }
    setGenerating(false)
  }
  const acceptItem = useMutation({ mutationFn: (itemId) => updateScopeItem(itemId, { is_accepted: true }), onSuccess: invalidate })
  const editItem = useMutation({ mutationFn: ({ itemId, description }) => updateScopeItem(itemId, { description }), onSuccess: invalidate })
  const removeItem = useMutation({ mutationFn: (itemId) => deleteScopeItem(itemId), onSuccess: invalidate })
  const acceptQ = useMutation({ mutationFn: (qId) => updateQuestion(qId, { is_accepted: true }), onSuccess: invalidate })
  const editQ = useMutation({ mutationFn: ({ qId, question_text }) => updateQuestion(qId, { question_text }), onSuccess: invalidate })
  const removeQ = useMutation({ mutationFn: (qId) => deleteQuestion(qId), onSuccess: invalidate })

  if (!scope || scope.status === 'not_started') {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
        <button onClick={() => navigate(`/engagements/${id}/planning`)} className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand">
          <ArrowLeft size={16} /> Back to planning
        </button>
        <h1 className="text-h1 text-fg">Scope & Objectives</h1>
        <p className="border border-line mt-6 rounded-xl bg-surface p-6 text-sm text-fg-muted">
          Nothing queued yet. Complete <span className="font-medium">Topic Intelligence</span> and accept the memo
          to populate scope items, questions, and frameworks here.
        </p>
      </div>
    )
  }

  const inScope = scope.items.filter((i) => i.item_type === 'in_scope')
  const outScope = scope.items.filter((i) => i.item_type === 'out_of_scope')

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
      <button onClick={() => navigate(`/engagements/${id}/planning`)} className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand">
        <ArrowLeft size={16} /> Back to planning
      </button>
      <h1 className="text-h1 text-fg">Scope & Objectives</h1>
      <p className="mt-1 text-sm text-fg-muted">Review and confirm each item. The badge names the step that proposed it.</p>

      <div className="border border-line mt-6 rounded-xl bg-surface p-5">
        <div className="mb-1 flex items-center justify-between">
          <label className="block text-xs font-semibold uppercase tracking-wide text-fg-muted">Overall objective</label>
          <div className="flex items-center gap-1">
            <button onClick={generateObjective} disabled={generating} className="flex items-center gap-1 text-xs text-brand hover:underline disabled:opacity-40">
              <Sparkles size={12} /> {generating ? 'Generating…' : 'Generate'}
            </button>
            <AIFieldHelper
              fieldLabel="Overall audit objective"
              currentValue={scope.overall_objective || ''}
              engagementId={id}
              onAccept={(v) => saveObjective.mutate(v)}
            />
          </div>
        </div>
        <EditableText value={scope.overall_objective || ''} onSave={(v) => saveObjective.mutate(v)} placeholder="Click to add the overall audit objective…" />
        {scope.scope_period && <p className="mt-3 text-xs text-fg-subtle">Scope period: {scope.scope_period}</p>}
      </div>

      <Section title={`In-scope items (${inScope.length})`}>
        {inScope.map((i) => (
          <ReviewRow key={i.id} accepted={i.is_accepted} row={i} engagementId={id}
            onAccept={() => acceptItem.mutate(i.id)} onDismiss={() => removeItem.mutate(i.id)} onRemove={() => removeItem.mutate(i.id)}>
            <EditableText value={i.description} onSave={(v) => editItem.mutate({ itemId: i.id, description: v })} />
            {i.rationale && <p className="px-2 text-xs text-fg-subtle">Basis: {i.rationale}</p>}
          </ReviewRow>
        ))}
        {inScope.length === 0 && <Empty />}
      </Section>

      <Section title={`Out-of-scope items (${outScope.length})`}>
        {outScope.map((i) => (
          <ReviewRow key={i.id} accepted={i.is_accepted} row={i} engagementId={id}
            onAccept={() => acceptItem.mutate(i.id)} onDismiss={() => removeItem.mutate(i.id)} onRemove={() => removeItem.mutate(i.id)}>
            <EditableText value={i.description} onSave={(v) => editItem.mutate({ itemId: i.id, description: v })} />
            {i.rationale && <p className="px-2 text-xs text-fg-subtle">Rationale: {i.rationale}</p>}
          </ReviewRow>
        ))}
        {outScope.length === 0 && <Empty />}
      </Section>

      <Section title={`Key audit questions (${scope.questions.length})`}>
        {scope.questions.map((q) => (
          <ReviewRow key={q.id} accepted={q.is_accepted} row={q} engagementId={id}
            onAccept={() => acceptQ.mutate(q.id)} onDismiss={() => removeQ.mutate(q.id)} onRemove={() => removeQ.mutate(q.id)}>
            <EditableText value={q.question_text} onSave={(v) => editQ.mutate({ qId: q.id, question_text: v })} />
            {q.regulatory_basis && <p className="px-2 text-xs text-fg-subtle">Basis: {q.regulatory_basis}</p>}
          </ReviewRow>
        ))}
        {scope.questions.length === 0 && <Empty />}
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="mt-8">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-fg-subtle">{title}</h2>
      <div className="space-y-2">{children}</div>
    </section>
  )
}
function Empty() {
  return <p className="text-sm text-fg-subtle">None.</p>
}
