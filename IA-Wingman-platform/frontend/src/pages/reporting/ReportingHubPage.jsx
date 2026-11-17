import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileText, Sparkles, Loader2, Plus, Trash2, FileDown, Scale, DownloadCloud, Gavel,
} from 'lucide-react'
import { getEngagement } from '../../api/engagements'
import {
  listFindings, seedFindings, createFinding, updateFinding, deleteFinding, draftFinding,
  getReport, draftReport, updateReport, exportReport,
} from '../../api/reporting'
import { useStore } from '../../store/useStore'
import PageContainer from '../../components/layout/PageContainer'
import { PageHeader } from '../../components/layout/PageHeader'
import { EntityBadge } from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { Card, SectionHeading } from '../../components/ui/Card'
import Collapsible from '../../components/ui/Collapsible'
import { SummaryCard } from '../../components/ui/ReadableOutput'
import ExplainabilityAnnex from '../../components/reporting/ExplainabilityAnnex'
import GroundedValidator from '../../components/reporting/GroundedValidator'
import RecordHistory from '../../components/ui/RecordHistory'

const RATING = {
  high: { label: 'High', cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25' },
  medium: { label: 'Medium', cls: 'text-sev-med bg-sev-med/12 ring-sev-med/25' },
  low: { label: 'Low', cls: 'text-sev-low bg-sev-low/12 ring-sev-low/25' },
}

function RatingPill({ rating }) {
  const r = RATING[rating]
  if (!r) return <span className="text-xs text-fg-subtle">unrated</span>
  return <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${r.cls}`}>{r.label}</span>
}

const FIVE_C = [
  { key: 'condition', label: 'Condition — what was found' },
  { key: 'criteria', label: 'Criteria — the norm' },
  { key: 'cause', label: 'Cause — root cause' },
  { key: 'effect', label: 'Effect — consequence/risk' },
  { key: 'recommendation', label: 'Recommendation — corrective action' },
]

function FindingCard({ engagementId, finding }) {
  const qc = useQueryClient()
  const [form, setForm] = useState(finding)
  const [dirty, setDirty] = useState(false)
  useEffect(() => { setForm(finding); setDirty(false) }, [finding])
  // The annex is derived from the finding — refresh it whenever the finding changes.
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['findings', engagementId] })
    qc.invalidateQueries({ queryKey: ['explainability', engagementId, finding.id] })
    qc.invalidateQueries({ queryKey: ['validation', engagementId, finding.id] })
    qc.invalidateQueries({ queryKey: ['history', 'findings', finding.id] })
  }

  const save = useMutation({
    mutationFn: () => updateFinding(engagementId, finding.id, {
      title: form.title, condition: form.condition, criteria: form.criteria,
      cause: form.cause, effect: form.effect, recommendation: form.recommendation, rating: form.rating,
    }),
    onSuccess: () => { setDirty(false); invalidate() },
  })
  const draft = useMutation({ mutationFn: () => draftFinding(engagementId, finding.id), onSuccess: invalidate })
  const remove = useMutation({ mutationFn: () => deleteFinding(engagementId, finding.id), onSuccess: invalidate })

  const set = (k, v) => { setForm((f) => ({ ...f, [k]: v })); setDirty(true) }
  const drafting = finding.status === 'drafting' || draft.isPending
  const challenge = finding.rating_challenge

  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <input
          value={form.title || ''}
          onChange={(e) => set('title', e.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-transparent bg-transparent px-1 py-0.5 text-sm font-semibold text-fg outline-none transition hover:border-line focus:border-brand"
        />
        <RatingPill rating={finding.rating} />
        <button onClick={() => remove.mutate()} className="rounded-lg p-1 text-fg-subtle transition hover:bg-surface-3 hover:text-sev-high" title="Delete">
          <Trash2 size={15} />
        </button>
      </div>

      {(finding.rating_rationale || challenge) && (
        <div className="mt-2 space-y-1.5">
          {finding.rating_rationale && <div className="text-xs text-fg-muted">Rationale: {finding.rating_rationale}</div>}
          {challenge && (
            <div className={`flex items-start gap-2 rounded-lg px-2 py-1.5 text-xs ring-1 ring-inset ${
              challenge.agrees ? 'bg-sev-low/8 ring-sev-low/20 text-sev-low'
                               : 'bg-sev-med/8 ring-sev-med/20 text-sev-med'}`}>
              <Gavel size={13} className="mt-0.5 shrink-0" />
              <span>
                <span className="font-semibold">Reviewer {challenge.agrees ? 'upholds' : `suggests ${RATING[challenge.suggested_rating]?.label || challenge.suggested_rating}`}:</span> {challenge.rationale}
              </span>
            </div>
          )}
        </div>
      )}

      <Collapsible title="5C detail" className="mt-3">
        <div className="space-y-3">
          {FIVE_C.map(({ key, label }) => (
            <div key={key}>
              <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-fg-subtle">{label}</label>
              <textarea
                value={form[key] || ''}
                onChange={(e) => set(key, e.target.value)}
                rows={2}
                className="w-full resize-y rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
              />
            </div>
          ))}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-medium uppercase tracking-wide text-fg-subtle">Rating</span>
            {['high', 'medium', 'low'].map((r) => (
              <button
                key={r}
                onClick={() => set('rating', r)}
                className={`rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset transition ${
                  form.rating === r ? RATING[r].cls : 'text-fg-muted ring-line hover:bg-surface-3'}`}
              >
                {RATING[r].label}
              </button>
            ))}
          </div>
        </div>
      </Collapsible>

      <ExplainabilityAnnex engagementId={engagementId} findingId={finding.id} />
      <GroundedValidator engagementId={engagementId} findingId={finding.id} />
      {/* The drafter overwrites what the auditor typed; this is where that shows. */}
      <RecordHistory entity="findings" entityId={finding.id} className="mt-3 border-t border-line pt-3" />

      <div className="mt-3 flex items-center gap-2">
        <Button onClick={() => draft.mutate()} disabled={drafting}>
          {drafting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
          {drafting ? 'Drafting…' : 'AI draft 5C + rating'}
        </Button>
        {dirty && <Button variant="secondary" onClick={() => save.mutate()} disabled={save.isPending}>Save</Button>}
      </div>
    </Card>
  )
}

// ── Report block ─────────────────────────────────────────────────────────────
const OPINION = {
  satisfactory: 'Satisfactory',
  needs_improvement: 'Needs improvement',
  unsatisfactory: 'Unsatisfactory',
}

function ReportBlock({ engagementId, findingCount }) {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['report', engagementId],
    queryFn: () => getReport(engagementId),
    refetchInterval: (q) => (q.state.data?.status === 'drafting' ? 2500 : false),
  })
  const [form, setForm] = useState({ exec_summary: '', conclusion: '' })
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    if (data) { setForm({ exec_summary: data.exec_summary || '', conclusion: data.conclusion || '' }); setDirty(false) }
  }, [data])

  const draft = useMutation({ mutationFn: () => draftReport(engagementId), onSuccess: () => qc.invalidateQueries({ queryKey: ['report', engagementId] }) })
  const save = useMutation({
    mutationFn: () => updateReport(engagementId, form),
    onSuccess: () => { setDirty(false); qc.invalidateQueries({ queryKey: ['report', engagementId] }) },
  })
  const drafting = data?.status === 'drafting' || draft.isPending
  const set = (k, v) => { setForm((f) => ({ ...f, [k]: v })); setDirty(true) }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          <Scale size={16} className="text-brand" /> Audit report
          {data?.overall_opinion && (
            <span className="rounded-full bg-surface-3 px-2 py-0.5 text-[11px] font-semibold text-fg-muted">
              {OPINION[data.overall_opinion] || data.overall_opinion}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => draft.mutate()} disabled={drafting || !findingCount}>
            {drafting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
            {drafting ? 'Drafting…' : 'AI draft report'}
          </Button>
          {data?.status === 'ready' && (
            <Button variant="secondary" onClick={() => exportReport(engagementId)}><FileDown size={15} /> Word</Button>
          )}
        </div>
      </div>

      {!findingCount && <p className="text-sm text-fg-muted">Add findings first — the report is drafted from them.</p>}

      <div>
        <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-fg-subtle">Executive summary</label>
        <textarea value={form.exec_summary} onChange={(e) => set('exec_summary', e.target.value)} rows={4}
          className="w-full resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20" />
      </div>
      <div>
        <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-fg-subtle">Conclusion</label>
        <textarea value={form.conclusion} onChange={(e) => set('conclusion', e.target.value)} rows={3}
          className="w-full resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20" />
      </div>
      {dirty && <Button variant="secondary" onClick={() => save.mutate()} disabled={save.isPending}>Save report</Button>}
    </div>
  )
}

export default function ReportingHubPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  useEffect(() => { if (eng) setActiveEngagement(eng) }, [eng, setActiveEngagement])

  const { data: findings = [] } = useQuery({
    queryKey: ['findings', id],
    queryFn: () => listFindings(id),
    refetchInterval: (q) => (q.state.data?.some((f) => f.status === 'drafting') ? 2500 : false),
  })
  const invalidate = () => qc.invalidateQueries({ queryKey: ['findings', id] })
  const seed = useMutation({ mutationFn: () => seedFindings(id), onSuccess: invalidate })
  const add = useMutation({ mutationFn: () => createFinding(id, { title: 'New finding' }), onSuccess: invalidate })

  const counts = findings.reduce((a, f) => { if (f.rating) a[f.rating] = (a[f.rating] || 0) + 1; return a }, {})

  return (
    <PageContainer>
      <PageHeader
        back={{ to: `/engagements/${id}/planning`, label: 'Planning' }}
        badges={eng && <EntityBadge entity={eng.entity} />}
        title="Reporting"
        subtitle={eng?.name}
        actions={
          <>
            <Button variant="secondary" onClick={() => seed.mutate()} disabled={seed.isPending}>
              <DownloadCloud size={15} /> Seed from fieldwork
            </Button>
            <Button onClick={() => add.mutate()} disabled={add.isPending}><Plus size={15} /> Finding</Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-3">
          <div className="flex items-center justify-between">
            <SectionHeading>Findings (5C)</SectionHeading>
            {findings.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-fg-muted">
                {counts.high ? <RatingPill rating="high" /> : null}
                {counts.medium ? <RatingPill rating="medium" /> : null}
                {counts.low ? <RatingPill rating="low" /> : null}
                <span>· {findings.length} total</span>
              </div>
            )}
          </div>
          {findings.length === 0 ? (
            <Card className="p-6 text-center text-sm text-fg-muted">
              No findings yet. Seed them from fieldwork observations, or add one manually.
            </Card>
          ) : (
            findings.map((f) => <FindingCard key={f.id} engagementId={id} finding={f} />)
          )}
        </div>

        <div className="lg:col-span-2">
          <SectionHeading>Report</SectionHeading>
          <Card className="mt-3 p-5"><ReportBlock engagementId={id} findingCount={findings.length} /></Card>
          <div className="mt-4">
            <SummaryCard title="Human-in-the-loop" icon={FileText}>
              <span className="text-xs">AI proposes the 5C structure, rating and report text. A second agent challenges each rating. You edit and sign — exports are marked "AI-assisted; reviewed by auditor".</span>
            </SummaryCard>
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
