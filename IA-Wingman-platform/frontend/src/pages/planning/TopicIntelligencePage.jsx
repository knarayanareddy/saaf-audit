import { Fragment, useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Upload, Plus, Trash2, FileText, Check,
  AlertTriangle, Loader2, Globe, Scale, ShieldAlert,
  TrendingUp, Building2, MessagesSquare, ChevronDown, ChevronUp, Lightbulb, ShieldCheck,
} from 'lucide-react'
import {
  getTopicIntelligence, updateTopicIntelligence, updateLens4,
  acceptTopicIntelligence, discardTopicIntelligence, resynthesizeTopicIntelligence,
  getScanContext, exportTopicMemoWord, rerunTopicLens,
} from '../../api/planning'
import { runAgentsV2, getAgentsStatus } from '../../api/agents'
import DocumentsUpload from '../../components/planning/DocumentsUpload'
import { getEngagement } from '../../api/engagements'
import client from '../../api/client'
import EditableText from '../../components/ui/EditableText'
import Button from '../../components/ui/Button'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import { Tag } from '../../components/ui/Badge'
import JurisdictionSelect from '../../components/planning/JurisdictionSelect'
import ReadableText from '../../components/ui/ReadableText'
import RecordHistory from '../../components/ui/RecordHistory'
import { useStore } from '../../store/useStore'
import Tooltip from '../../components/ui/Tooltip'

function LensStatusIcon({ isComplete, isFailed }) {
  if (isComplete) return <Check className="h-5 w-5 text-sev-low" />
  if (isFailed) return <AlertTriangle className="h-5 w-5 text-sev-high" />
  return <Loader2 className="h-5 w-5 animate-spin text-brand" />
}

// What the lens's searching did, as the tool reported it. A lens can write
// "live web search was unavailable" for three different reasons — search was
// off, it ran out of searches, or the tool actually failed — and the summary
// alone cannot tell them apart. This line can.
function SearchLine({ search }) {
  if (!search) return null // a run from before this was recorded: claim nothing

  const { web_search: on, used, allowed, errors = [], retried, queries = [], sources_from_search: fromSearch } = search
  const codes = [...new Set(errors)]

  let tone = 'text-fg-subtle'
  let text
  if (!on) {
    text = 'Live search was off — built-in knowledge only.'
  } else if (codes.length) {
    tone = 'text-sev-high'
    text = `Live search hit errors (${codes.join(', ')}) after ${used} of ${allowed} searches.`
  } else if (used === 0) {
    tone = 'text-sev-high'
    text = retried
      ? 'Live search was on, but the lens ran no searches, even when asked again. Treat this summary as written from memory and verify it.'
      : 'Live search was on, but the lens ran no searches. Treat this summary as written from memory and verify it.'
  } else if (used >= allowed) {
    tone = 'text-sev-med'
    text = `Used all ${allowed} searches — it may have wanted more.${retried ? ' It searched only on a second attempt.' : ''}`
  } else {
    text = `${used} of ${allowed} searches used.${retried ? ' It searched only on a second attempt.' : ''}`
  }

  return (
    <div>
      <p className={`text-xs ${tone}`}>{text}</p>
      {fromSearch && (
        <p className="text-xs text-fg-subtle">
          The lens listed no sources itself, so the pages its searches returned are shown instead.
        </p>
      )}
      {queries.length > 0 && (
        <details className="mt-1 text-xs text-fg-muted">
          <summary className="cursor-pointer select-none text-fg-subtle hover:text-fg">
            What it searched for ({queries.length})
          </summary>
          <ol className="mt-1 list-decimal space-y-0.5 pl-5">
            {queries.map((q, i) => <li key={i}>{q}</li>)}
          </ol>
        </details>
      )}
    </div>
  )
}

const VERDICT_STYLE = {
  confirmed: { label: 'Confirmed', cls: 'bg-sev-low/10 text-sev-low' },
  corrected: { label: 'Corrected', cls: 'bg-sev-high/10 text-sev-high' },
  not_found: { label: 'Not settled', cls: 'bg-surface-3 text-fg-muted' },
}

// The round that goes back to the statements the lenses left open. It shows what was
// checked and what it found, and a statement it could not settle stays called open.
function VerificationCard({ verification }) {
  if (!verification) return null
  const { checks = [], searches_used: used = 0, searches_allowed: allowed = 0, queries = [] } = verification
  return (
    <div className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center gap-3 px-6 py-4">
        <ShieldCheck className="h-5 w-5 shrink-0 text-brand" />
        <div className="flex-1">
          <p className="font-semibold text-fg">Verification</p>
          <p className="text-xs text-fg-muted">
            A second look at what the lenses left open · {used} of {allowed} searches used
          </p>
        </div>
      </div>
      <div className="space-y-3 border-t border-line px-6 py-4">
        {checks.length === 0 && (
          <p className="text-sm text-fg-subtle">Nothing in the lens summaries needed checking.</p>
        )}
        {checks.map((c, i) => {
          const v = VERDICT_STYLE[c.verdict] || VERDICT_STYLE.not_found
          return (
            <div key={i} className="rounded-lg border border-line p-3">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${v.cls}`}>{v.label}</span>
                <p className="text-sm font-medium text-fg">{c.claim}</p>
              </div>
              <p className="text-xs text-fg-muted">{c.finding}</p>
              {c.source_url && (
                <a href={c.source_url} target="_blank" rel="noreferrer" className="mt-1 block truncate text-xs text-brand hover:underline">
                  {c.source_url}
                </a>
              )}
            </div>
          )
        })}
        {queries.length > 0 && (
          <details className="text-xs text-fg-muted">
            <summary className="cursor-pointer select-none text-fg-subtle hover:text-fg">What it searched for ({queries.length})</summary>
            <ol className="mt-1 list-decimal space-y-0.5 pl-5">
              {queries.map((q, i) => <li key={i}>{q}</li>)}
            </ol>
          </details>
        )}
      </div>
    </div>
  )
}

function LensCard({ icon: Icon, title, subtitle, summary, sources, search, patchKey, onPatch, error, onRerun, children }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="rounded-xl border border-line bg-surface shadow-sm">
      <button
        className="flex w-full items-center gap-3 px-6 py-4 text-left"
        onClick={() => setOpen(!open)}
      >
        <Icon className="h-5 w-5 text-brand shrink-0" />
        <div className="flex-1">
          <p className="font-semibold text-fg">{title}</p>
          {subtitle && <p className="text-xs text-fg-muted">{subtitle}</p>}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-fg-subtle" /> : <ChevronDown className="h-4 w-4 text-fg-subtle" />}
      </button>
      {open && (
        <div className="border-t border-line px-6 py-4 space-y-4">
          {summary !== undefined && (
            <EditableText
              value={summary ?? ''}
              onSave={(v) => onPatch({ [patchKey]: v })}
              placeholder="No summary generated — you can type one manually."
              multiline
              readable
            />
          )}
          {children}
          <SearchLine search={search} />
          {error && (
            <p className="text-xs text-sev-high">
              The last re-run of this lens failed ({error}). The result below is the earlier one.
            </p>
          )}
          {onRerun && (
            <button
              type="button"
              onClick={onRerun}
              title="Run only this lens again. The other lenses, the proposal and your selections stay as they are."
              className="text-xs font-medium text-brand hover:underline"
            >
              Re-run this lens only
            </button>
          )}
          {sources?.length > 0 && (
            <div className="border-t border-line pt-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle mb-2">Sources</p>
              <ul className="space-y-1">
                {sources.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-fg-muted">
                    <Globe className="mt-0.5 h-3 w-3 shrink-0 text-fg-subtle" />
                    <span>
                      {s.url ? (
                        <a
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline text-brand"
                        >
                          {s.title || s.url}
                        </a>
                      ) : (
                        s.title
                      )}
                      {s.date && <span className="text-fg-subtle ml-1">({s.date})</span>}
                      {s.confidence && (
                        <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          s.confidence === 'high' ? 'bg-sev-low/10 text-sev-low' :
                          s.confidence === 'medium' ? 'bg-sev-med/10 text-sev-med' :
                          'bg-surface-3 text-fg-muted'
                        }`}>{s.confidence}</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const PROPOSAL_CONFIDENCE_STYLES = {
  high: 'bg-sev-low/10 text-sev-low',
  medium: 'bg-sev-med/10 text-sev-med',
  low: 'bg-surface-3 text-fg-muted',
}

// interview_agenda.sponsor/.sme items are {id, question_text, included} objects
// (mirroring KeyAuditQuestion.question_text, the column they cascade into) —
// confirmed backend contract. ia_prework stays a plain string array (read-only,
// never cascades). Stays defensive and also accepts a bare string just in case.
function questionText(item) {
  if (typeof item === 'string') return item
  return item?.question_text ?? item?.text ?? ''
}

const FRAMEWORK_TIER_LABEL = {
  core: 'Core · selected',
  supporting: 'Supporting · add if relevant',
  optional: 'Optional · only if the scope grows',
}

function ProposalSection({ title, children }) {
  return (
    <section>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-subtle">{title}</h3>
      <div className="space-y-2">{children}</div>
    </section>
  )
}

function ProposalRow({ item, onToggle, children }) {
  const included = item.included !== false
  return (
    <label className={`flex cursor-pointer items-start gap-2 rounded-lg border border-line bg-surface p-3 transition-opacity ${included ? '' : 'opacity-50'}`}>
      <input
        type="checkbox"
        checked={included}
        onChange={onToggle}
        className="mt-1 h-4 w-4 shrink-0 rounded border-line-strong accent-brand"
      />
      <div className="min-w-0 flex-1">{children}</div>
    </label>
  )
}

function ScopingProposalCard({ ti, includedCount, totalCount, onToggle, onToggleInterview, onSaveConclusion, resynthesize }) {
  const keyRiskAreas = ti.key_risk_areas || []
  const excludedAreas = ti.excluded_areas || []
  const sponsorQs = ti.interview_agenda?.sponsor || []
  const smeQs = ti.interview_agenda?.sme || []
  const iaPreworkQs = ti.interview_agenda?.ia_prework || []
  const keyAuditQs = ti.interview_agenda?.key_audit_questions || []
  const proposedFrameworks = ti.proposed_frameworks || []

  return (
    <div className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="px-6 py-4">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-brand" />
          <p className="font-semibold text-fg">Scoping proposal</p>
          {!ti.synthesis_failed && (
            <span className="ml-auto rounded-full bg-brand-subtle px-2 py-1 text-xs font-semibold text-brand">
              {includedCount} of {totalCount} selected
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-fg-muted">
          Reconstructed from the three lenses above. Uncheck anything you don't want to carry forward —
          checked items are queued to Scope, Frameworks &amp; Interview Questions for a second review once you accept.
        </p>
      </div>

      <div className="border-t border-line px-6 py-4">
        {ti.synthesis_failed ? (
          <div className="flex items-center justify-between rounded-xl bg-sev-high/10 px-4 py-3 text-sm text-sev-high">
            <span>Could not reconcile the lenses into a scoping proposal.</span>
            {resynthesize.isPending ? (
              <span className="flex items-center gap-1 text-xs font-medium text-brand">
                <Loader2 className="animate-spin" size={12} /> Retrying…
              </span>
            ) : (
              <button onClick={() => resynthesize.mutate()} className="text-xs font-medium text-brand hover:underline">
                Retry synthesis →
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-5">
            <ProposalSection title={`Key risk areas (${keyRiskAreas.length})`}>
              {keyRiskAreas.map((area) => (
                <ProposalRow key={area.id} item={area} onToggle={() => onToggle('key_risk_areas', area.id)}>
                  <p className="text-sm font-medium text-fg">{area.title}</p>
                  {area.rationale && <p className="mt-0.5 text-xs text-fg-muted">{area.rationale}</p>}
                  {area.basis && <p className="mt-0.5 text-xs text-fg-subtle">Basis: {area.basis}</p>}
                </ProposalRow>
              ))}
              {keyRiskAreas.length === 0 && <p className="text-sm text-fg-subtle">None proposed.</p>}
            </ProposalSection>

            <ProposalSection title={`Excluded areas (${excludedAreas.length})`}>
              {excludedAreas.map((area) => (
                <ProposalRow key={area.id} item={area} onToggle={() => onToggle('excluded_areas', area.id)}>
                  <p className="text-sm font-medium text-fg">{area.title}</p>
                  {area.rationale && <p className="mt-0.5 text-xs text-fg-muted">{area.rationale}</p>}
                </ProposalRow>
              ))}
              {excludedAreas.length === 0 && <p className="text-sm text-fg-subtle">None proposed.</p>}
            </ProposalSection>

            <ProposalSection title={`Key audit questions (${keyAuditQs.length})`}>
              <p className="text-xs text-fg-subtle">What the audit as a whole must be able to answer. They go to Scope &amp; Objectives.</p>
              {keyAuditQs.map((q) => (
                <ProposalRow key={q.id} item={q} onToggle={() => onToggleInterview('key_audit_questions', q.id)}>
                  <p className="text-sm text-fg">{questionText(q)}</p>
                </ProposalRow>
              ))}
              {keyAuditQs.length === 0 && <p className="text-sm text-fg-subtle">None proposed.</p>}
            </ProposalSection>

            <ProposalSection title="Interview questions">
              <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">Sponsor · for the kick-off meeting</p>
              <div className="space-y-2">
                {sponsorQs.map((q) => (
                  <ProposalRow key={q.id} item={q} onToggle={() => onToggleInterview('sponsor', q.id)}>
                    <p className="text-sm text-fg">{questionText(q)}</p>
                  </ProposalRow>
                ))}
                {sponsorQs.length === 0 && <p className="text-sm text-fg-subtle">None proposed.</p>}
              </div>

              <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-fg-subtle">Experts (SME) · for the interviews</p>
              <div className="space-y-2">
                {smeQs.map((q) => (
                  <ProposalRow key={q.id} item={q} onToggle={() => onToggleInterview('sme', q.id)}>
                    <p className="text-sm text-fg">{questionText(q)}</p>
                  </ProposalRow>
                ))}
                {smeQs.length === 0 && <p className="text-sm text-fg-subtle">None proposed.</p>}
              </div>

              {iaPreworkQs.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">IA prework</p>
                  <p className="mb-2 mt-0.5 text-xs text-fg-subtle">
                    Preparation tasks for the team — does not cascade as an audit question.
                  </p>
                  <div className="space-y-1.5">
                    {iaPreworkQs.map((q, i) => (
                      <div key={q.id ?? i} className="rounded-lg border border-line bg-surface-3 px-3 py-2 text-sm text-fg-muted">
                        {questionText(q)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </ProposalSection>

            <ProposalSection title={`Proposed frameworks (${proposedFrameworks.length})`}>
              <p className="text-xs text-fg-subtle">
                Start from the core ones: the audit cannot be done without them. Supporting and optional ones are
                there to add if the scope needs them.
              </p>
              {proposedFrameworks.map((fw, i) => (
                <Fragment key={fw.id}>
                {(i === 0 || (proposedFrameworks[i - 1].tier || 'supporting') !== (fw.tier || 'supporting')) && (
                  <p className="pt-1 text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                    {FRAMEWORK_TIER_LABEL[fw.tier || 'supporting']}
                  </p>
                )}
                <ProposalRow item={fw} onToggle={() => onToggle('proposed_frameworks', fw.id)}>
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    {fw.is_primary && (
                      <span className="rounded bg-brand-subtle px-2 py-0.5 text-[10px] font-semibold uppercase text-brand">Primary</span>
                    )}
                    {fw.jurisdiction && (
                      <span className="rounded bg-surface-3 px-2 py-0.5 text-[10px] font-semibold uppercase text-fg-muted">{fw.jurisdiction}</span>
                    )}
                    {fw.confidence && (
                      <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${PROPOSAL_CONFIDENCE_STYLES[fw.confidence] || 'bg-surface-3 text-fg-muted'}`}>
                        {fw.confidence} confidence
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-fg">{fw.framework_name}</p>
                  {fw.applicability_rationale && <p className="mt-0.5 text-xs text-fg-muted">{fw.applicability_rationale}</p>}
                </ProposalRow>
                </Fragment>
              ))}
              {proposedFrameworks.length === 0 && <p className="text-sm text-fg-subtle">None proposed.</p>}
            </ProposalSection>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-fg-muted">Conclusion</label>
              <EditableText
                value={ti.conclusion ?? ''}
                onSave={onSaveConclusion}
                placeholder="No conclusion generated — you can type one manually."
                multiline
                readable
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function TopicIntelligencePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const [urls, setUrls] = useState([])
  const [urlInput, setUrlInput] = useState('')
  const [manualKeyword, setManualKeyword] = useState('')
  const [extraContext, setExtraContext] = useState('')
  const [summary, setSummary] = useState(null)
  const [lens4Draft, setLens4Draft] = useState('')
  const [discardConfirm, setDiscardConfirm] = useState(false)

  // ── Queries ──
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => client.get('/health').then((r) => r.data),
    staleTime: 60_000,
  })
  const webSearchEnabled = health?.web_search_enabled ?? false

  const { data: engagement } = useQuery({
    queryKey: ['engagement', id],
    queryFn: () => getEngagement(id),
    staleTime: 60_000,
  })

  const { data: ti, refetch: refetchTi } = useQuery({
    queryKey: ['ti', id],
    queryFn: () => getTopicIntelligence(id),
    refetchInterval: (q) => (q.state.data?.status === 'agents_pending' ? 3000 : false),
  })

  const { data: scanContext } = useQuery({
    queryKey: ['scan-context', id],
    queryFn: () => getScanContext(id),
    staleTime: 30_000,
  })

  // The box starts filled with whatever a previous scan ran on, so a re-run
  // builds on that instead of starting blank.
  useEffect(() => {
    if (scanContext?.extra_context) setExtraContext(scanContext.extra_context)
  }, [scanContext?.extra_context])

  const { data: agentStatus = {} } = useQuery({
    queryKey: ['agent-status', id],
    queryFn: () => getAgentsStatus(id),
    refetchInterval: (q) => {
      const data = q.state.data
      if (!data) return false
      const anyRunning = Object.values(data).some(
        (r) => r.status === 'pending' || r.status === 'running',
      )
      return anyRunning ? 3000 : false
    },
    enabled: ti?.status === 'agents_pending',
  })

  // Sync lens4Draft from server data
  useEffect(() => {
    if (ti?.lens4_notes !== undefined) setLens4Draft(ti.lens4_notes ?? '')
  }, [ti?.lens4_notes])

  // ── Mutations ──

  const run = useMutation({
    mutationFn: () =>
      runAgentsV2(id, {
        urls,
        use_web_search: webSearchEnabled,
        custom_queries: [],
        manual_keyword: manualKeyword || '',
        extra_context: extraContext || '',
      }),
    onSuccess: () => {
      refetchTi()
      qc.invalidateQueries({ queryKey: ['agent-status', id] })
    },
  })

  const patch = useMutation({
    mutationFn: (p) => updateTopicIntelligence(id, p),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ti', id] }),
  })

  const saveLens4 = useMutation({
    mutationFn: (payload) => updateLens4(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ti', id] }),
  })

  const accept = useMutation({
    mutationFn: () => acceptTopicIntelligence(id),
    onSuccess: (data) => setSummary(data),
  })

  const discard = useMutation({
    mutationFn: () => discardTopicIntelligence(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ti', id] })
      qc.invalidateQueries({ queryKey: ['agent-status', id] })
    },
  })

  const rerunLens = useMutation({
    mutationFn: (lens) => rerunTopicLens(id, lens),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ti', id] })
      qc.invalidateQueries({ queryKey: ['agent-status', id] })
    },
  })
  // Only a memo the auditor has not accepted can have a lens replaced.
  const canRerunLens = ti?.status === 'review' && !ti?.memo_accepted && !rerunLens.isPending

  const resynthesize = useMutation({
    mutationFn: () => resynthesizeTopicIntelligence(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ti', id] }),
    onError: (err) => showToast(err.response?.data?.detail || 'Could not retry synthesis', 'error'),
  })

  // Optimistic: write the toggled array straight into the query cache so the
  // checkbox and the "N of M selected" count update instantly, then persist
  // through the same generic PATCH the lens summaries already use. Its
  // onSuccess already invalidates ['ti', id], which reconciles with the
  // server afterwards — no separate rollback path needed since the payload
  // we send IS the desired new state.
  const toggleIncluded = (field, itemId) => {
    const list = ti?.[field] || []
    const updated = list.map((it) => (it.id === itemId ? { ...it, included: !(it.included !== false) } : it))
    qc.setQueryData(['ti', id], (old) => (old ? { ...old, [field]: updated } : old))
    patch.mutate({ [field]: updated })
  }

  const toggleInterviewIncluded = (subKey, itemId) => {
    const agenda = ti?.interview_agenda || {}
    const list = agenda[subKey] || []
    const updated = list.map((it) => (it.id === itemId ? { ...it, included: !(it.included !== false) } : it))
    const newAgenda = { ...agenda, [subKey]: updated }
    qc.setQueryData(['ti', id], (old) => (old ? { ...old, interview_agenda: newAgenda } : old))
    patch.mutate({ interview_agenda: newAgenda })
  }

  const Back = () => (
    <button
      onClick={() => navigate(`/engagements/${id}/planning`)}
      className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
    >
      <ArrowLeft size={16} /> Back to planning
    </button>
  )

  // ── State D: Saved (after accept) ──
  if (summary) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
        <div className="rounded-xl border border-sev-low/25 bg-sev-low/10 p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-sev-low/10">
              <Check className="h-5 w-5 text-sev-low" />
            </div>
            <div>
              <p className="font-semibold text-sev-low">Topic Intelligence scan accepted</p>
              <p className="text-sm text-sev-low">
                {summary.scope_items_queued ?? 0} scope items · {summary.questions_queued ?? 0} audit questions · {summary.frameworks_queued ?? 0} frameworks
              </p>
            </div>
          </div>
        </div>
        <div className="mt-6 flex gap-3">
          <Button variant="ghost" onClick={() => navigate(`/engagements/${id}/planning`)}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to planning
          </Button>
          <Button onClick={() => navigate(`/engagements/${id}/planning/scope-objectives`)}>
            Review scope →
          </Button>
        </div>
      </div>
    )
  }

  // ── State C: Review ──
  if (ti?.status === 'review' || ti?.status === 'agreed') {
    const keyRiskAreasT = ti.key_risk_areas || []
    const excludedAreasT = ti.excluded_areas || []
    const proposedFrameworksT = ti.proposed_frameworks || []
    const keyAuditQsT = ti.interview_agenda?.key_audit_questions || []
    const tallyItems = [...keyRiskAreasT, ...excludedAreasT, ...keyAuditQsT, ...proposedFrameworksT]
    const totalCount = tallyItems.length
    const includedCount = tallyItems.filter((it) => it.included !== false).length
    const hasSynthesis = ti.synthesis_failed || totalCount > 0
      || (ti.interview_agenda?.ia_prework?.length > 0) || !!ti.conclusion

    return (
      <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
        <Back />
        <h1 className="text-h1 text-fg">Topic Intelligence</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Review the 4-lens scan. Edit any lens summary, add internal context, then send to Audit Intelligence.
        </p>

        {ti.topic_primer && (
          <div className="mt-6 rounded-xl border border-brand/20 bg-brand-subtle/30 p-5">
            <div className="mb-2 flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-brand" />
              <p className="font-semibold text-fg">What is this topic?</p>
              <span className="ml-auto text-xs text-fg-subtle">Plain-language primer</span>
            </div>
            <ReadableText value={ti.topic_primer} />
          </div>
        )}

        <div className="mt-6 space-y-4">
          <LensCard
            icon={Scale}
            title="Normative & Regulatory"
            subtitle="Formal law · Directives · EBA/ESMA guidelines"
            summary={ti.lens1_summary}
            sources={ti.lens1_sources}
            search={ti.lens1_search}
            error={ti.lens_errors?.lens1}
            onRerun={canRerunLens ? () => rerunLens.mutate(1) : undefined}
            patchKey="lens1_summary"
            onPatch={(p) => patch.mutate(p)}
          />

          <LensCard
            icon={ShieldAlert}
            title="Supervisory & Enforcement"
            subtitle="Supervisor priorities · Thematic reviews · Enforcement actions"
            summary={ti.lens2_summary}
            sources={ti.lens2_sources}
            search={ti.lens2_search}
            error={ti.lens_errors?.lens2}
            onRerun={canRerunLens ? () => rerunLens.mutate(2) : undefined}
            patchKey="lens2_summary"
            onPatch={(p) => patch.mutate(p)}
          />

          <LensCard
            icon={TrendingUp}
            title="Society, Trends & Incidents"
            subtitle="Media · Political agenda · Peer incidents · Emerging risks"
            summary={ti.lens3_summary}
            sources={ti.lens3_sources}
            search={ti.lens3_search}
            error={ti.lens_errors?.lens3}
            onRerun={canRerunLens ? () => rerunLens.mutate(3) : undefined}
            patchKey="lens3_summary"
            onPatch={(p) => patch.mutate(p)}
          >
            {ti.lens3_sources?.[0]?.materiality_signal && (
              <div className="rounded-lg bg-sev-med/10 border border-sev-med/25 px-4 py-2 text-sm text-sev-med">
                <span className="font-semibold">Materiality signal: </span>
                {ti.lens3_sources[0].materiality_signal}
              </div>
            )}
          </LensCard>

          <VerificationCard verification={ti.verification} />

          {/* Lens 4 — Internal Context (manual, always editable) */}
          <div className="rounded-xl border border-line bg-surface shadow-sm">
            <div className="flex items-center gap-3 px-6 py-4">
              <Building2 className="h-5 w-5 text-brand" />
              <div className="flex-1">
                <p className="font-semibold text-fg">Internal Context</p>
                <p className="text-xs text-fg-muted">Platform memory · Prior findings · Open recommendations</p>
              </div>
              <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                ti.lens4_state === 'rich' ? 'bg-sev-low/10 text-sev-low' :
                ti.lens4_state === 'partial' ? 'bg-sev-med/10 text-sev-med' :
                'bg-surface-3 text-fg-muted'
              }`}>
                {ti.lens4_state === 'rich' ? 'Rich' : ti.lens4_state === 'partial' ? 'Partial' : 'Empty'}
              </span>
            </div>
            <div className="border-t border-line px-6 py-4">
              {(ti.lens4_state === 'empty' || !ti.lens4_state) && (
                <p className="mb-3 text-sm text-fg-muted">
                  No internal context added. This is your first audit on this topic, or no prior findings are
                  recorded here. You can add context manually below.
                </p>
              )}
              <textarea
                value={lens4Draft}
                onChange={(e) => setLens4Draft(e.target.value)}
                onBlur={() => {
                  const trimmed = lens4Draft.trim()
                  const newState = trimmed ? 'partial' : 'empty'
                  saveLens4.mutate({ notes: lens4Draft, state: newState })
                }}
                placeholder="Paste prior findings, open recommendations, or known risks here."
                className="w-full rounded-lg border border-line px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-1 focus:ring-brand resize-none"
                rows={5}
              />
              <div className="mt-4">
                <DocumentsUpload engagementId={id} title="Internal documents (drag & drop)" />
              </div>
            </div>
          </div>

          {hasSynthesis && (
            <ScopingProposalCard
              ti={ti}
              includedCount={includedCount}
              totalCount={totalCount}
              onToggle={toggleIncluded}
              onToggleInterview={toggleInterviewIncluded}
              onSaveConclusion={(v) => patch.mutate({ conclusion: v })}
              resynthesize={resynthesize}
            />
          )}

        </div>

        {/* Which lens wrote what, with which model and prompt — and what the
            auditor changed afterwards. */}
        <RecordHistory entity="topic_intelligence" entityId={ti.id} className="mt-6 rounded-xl border border-line bg-surface px-6 py-4" />

        {/* Handover bar */}
        {ti.status !== 'agreed' ? (
          <div className="sticky bottom-0 mt-6 border-t border-line bg-surface px-6 py-4 shadow-[0_-2px_8px_rgba(0,0,0,0.06)] flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-fg">Ready to hand over to Audit Intelligence?</p>
              <p className="text-xs text-fg-subtle">
                {hasSynthesis && !ti.synthesis_failed
                  ? `Sends ${includedCount} item${includedCount === 1 ? '' : 's'} to Scope, Frameworks & Interview Questions for final review.`
                  : 'Review the 4 lenses, then send to ANL, Scope & Objectives, and Frameworks.'}
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="ghost" onClick={() => exportTopicMemoWord(id)}>
                <FileText className="mr-2 h-4 w-4" /> Word
              </Button>
              <Button variant="ghost" onClick={() => setDiscardConfirm(true)}>
                Discard & re-run
              </Button>
              <Button onClick={() => accept.mutate()} disabled={accept.isPending}>
                {accept.isPending ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving…</>
                ) : (
                  <><Check className="mr-2 h-4 w-4" /> Send to Audit Intelligence →</>
                )}
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-6 rounded-xl bg-sev-low/10 border border-sev-low/25 px-6 py-4">
            <p className="text-sm font-medium text-sev-low">
              <Check className="inline h-4 w-4 mr-1" /> Scan accepted — data forwarded to downstream modules.
            </p>
            <button
              type="button"
              onClick={() => exportTopicMemoWord(id)}
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-brand hover:underline"
            >
              <FileText className="h-3.5 w-3.5" /> Download the memo as Word
            </button>
          </div>
        )}
        <ConfirmDialog
          open={discardConfirm}
          onClose={() => setDiscardConfirm(false)}
          onConfirm={() => { setDiscardConfirm(false); discard.mutate() }}
          title="Discard this scan?"
          description="This removes the current Topic Intelligence scan and its lenses so you can start over. This cannot be undone."
          confirmLabel="Discard & re-run"
          tone="danger"
          loading={discard.isPending}
        />
      </div>
    )
  }

  // ── State B: Agents running ──
  if (ti?.status === 'agents_pending') {
    const lensState = (key) => {
      const r = agentStatus?.[key]
      const s = r?.status || 'pending'
      return { isComplete: s === 'complete', isFailed: s === 'failed' }
    }
    const synthesizing = (ti?.progress_pct ?? 0) >= 50

    return (
      <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
        <Back />
        <div className="flex items-center gap-3 mb-2">
          <Loader2 className="h-6 w-6 animate-spin text-brand" />
          <h1 className="text-h1 text-fg">Scan in progress…</h1>
        </div>
        <p className="mb-6 text-sm text-fg-muted">Reading sources and analysing — typically 1–3 minutes.</p>

        <div className="space-y-3">
          {/* Lens 1 */}
          <div className="rounded-lg border bg-surface p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <Scale className="h-5 w-5 text-brand" />
              <div>
                <p className="font-medium text-fg">Normative & Regulatory</p>
                <p className="text-xs text-fg-muted">Legislation · Guidelines · EBA standards</p>
              </div>
              <div className="ml-auto">
                <LensStatusIcon {...lensState('lens1')} />
              </div>
            </div>
          </div>

          {/* Lens 2 */}
          <div className="rounded-lg border bg-surface p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-5 w-5 text-brand" />
              <div>
                <p className="font-medium text-fg">Supervisory & Enforcement</p>
                <p className="text-xs text-fg-muted">Supervisor focus · Enforcement actions</p>
              </div>
              <div className="ml-auto">
                <LensStatusIcon {...lensState('lens2')} />
              </div>
            </div>
          </div>

          {/* Lens 3 */}
          <div className="rounded-lg border bg-surface p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <TrendingUp className="h-5 w-5 text-brand" />
              <div>
                <p className="font-medium text-fg">Society, Trends & Incidents</p>
                <p className="text-xs text-fg-muted">Media · Peers · Emerging risks</p>
              </div>
              <div className="ml-auto">
                <LensStatusIcon {...lensState('lens3')} />
              </div>
            </div>
          </div>

          {synthesizing && (
            <div className="rounded-lg border bg-surface p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <Lightbulb className="h-5 w-5 text-brand" />
                <div>
                  <p className="font-medium text-fg">Reconciling into a scoping proposal</p>
                  <p className="text-xs text-fg-muted">Combining the three lenses into key risks, exclusions, interview questions, and applicable frameworks.</p>
                </div>
                <div className="ml-auto"><Loader2 className="h-5 w-5 animate-spin text-brand" /></div>
              </div>
            </div>
          )}

          {/* Lens 4 — manual, immediately editable while agents run */}
          <div className="rounded-lg border bg-surface p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="h-5 w-5 text-brand" />
              <p className="font-medium text-fg">Internal Context</p>
              <span className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full bg-surface-3 text-fg-muted">
                Manual
              </span>
            </div>
            <p className="text-xs text-fg-muted mb-2">You can add internal context while the scan runs.</p>
            <textarea
              value={lens4Draft}
              onChange={(e) => setLens4Draft(e.target.value)}
              onBlur={() => {
                if (lens4Draft !== (ti?.lens4_notes ?? '')) {
                  saveLens4.mutate({
                    notes: lens4Draft,
                    state: lens4Draft.trim() ? 'partial' : 'empty',
                  })
                }
              }}
              placeholder="Paste prior findings, open recommendations, or known risks here."
              className="w-full rounded-lg border border-line px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-1 focus:ring-brand resize-none"
              rows={4}
            />
            <div className="mt-4">
              <DocumentsUpload engagementId={id} title="Internal documents (drag & drop)" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── State A: Setup ──
  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
      <Back />
      <h1 className="text-h1 text-fg">Topic Intelligence</h1>
      <p className="mt-1 text-sm text-fg-muted">Understand the audit topic before making scoping decisions.</p>

      {/* Section 0: Jurisdictions in scope */}
      <section className="mt-6">
        <JurisdictionSelect engagementId={id} />
      </section>

      {/* Section 1: Upload documents (shared component — drag & drop, PDF/Word/text) */}
      <section className="mt-6">
        <DocumentsUpload engagementId={id} title="Uploaded documents" />
      </section>

      {/* Section 2: External sources */}
      <section className="mt-6">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">External sources (optional)</h2>
        <p className="mb-2 text-xs text-fg-subtle">Add specific URLs — e.g. a DNB press release or EBA guideline.</p>
        <div className="flex gap-2">
          <input
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && urlInput.trim()) {
                setUrls([...urls, urlInput.trim()])
                setUrlInput('')
              }
            }}
            placeholder="https://…"
            className="flex-1 rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-brand"
          />
          <Button
            variant="secondary"
            onClick={() => {
              if (urlInput.trim()) {
                setUrls([...urls, urlInput.trim()])
                setUrlInput('')
              }
            }}
          >
            <Plus size={16} /> Add URL
          </Button>
        </div>
        <div className="mt-2 space-y-1">
          {urls.map((u, i) => (
            <div key={i} className="border border-line flex items-center justify-between rounded-lg bg-surface px-3 py-1.5 text-xs">
              <span className="truncate text-fg-muted">{u}</span>
              <Tooltip label="Remove this source" side="left">
                <button
                  onClick={() => setUrls(urls.filter((_, j) => j !== i))}
                  aria-label="Remove this source"
                  className="text-fg-subtle hover:text-sev-high"
                >
                  <Trash2 size={12} />
                </button>
              </Tooltip>
            </div>
          ))}
        </div>
      </section>

      {/* Section 3: 4-lens preview + keyword */}
      <section className="mt-6">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-fg-muted">What the scan covers</h2>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {[
            { icon: Scale, title: 'Normative & Regulatory', desc: 'Formal law & guidelines' },
            { icon: ShieldAlert, title: 'Supervisory & Enforcement', desc: 'Supervisor priorities & enforcement' },
            { icon: TrendingUp, title: 'Society, Trends & Incidents', desc: 'Media, peers, incidents' },
            { icon: Building2, title: 'Internal Context', desc: 'Your internal knowledge (manual)' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-lg border border-line bg-surface px-4 py-3 shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <Icon className="h-4 w-4 text-brand" />
                <p className="text-sm font-medium text-fg">{title}</p>
              </div>
              <p className="text-xs text-fg-subtle">{desc}</p>
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-brand/20 bg-brand-subtle/30 p-4">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-semibold text-fg">Focus keyword</h3>
            <span className="text-xs font-normal text-fg-subtle">(optional)</span>
            {webSearchEnabled ? (
              <span className="ml-auto rounded bg-sev-low/10 px-1.5 py-0.5 text-[10px] font-bold uppercase text-sev-low">
                Live search ON
              </span>
            ) : (
              <span className="ml-auto rounded bg-surface-3 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-fg-subtle">
                Built-in knowledge only
              </span>
            )}
          </div>
          <input
            value={manualKeyword}
            onChange={(e) => setManualKeyword(e.target.value)}
            placeholder="e.g. DORA, DNB thematic review, complaints handling, EDD…"
            maxLength={200}
            className="w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-brand"
          />
          {manualKeyword.trim() && (
            <p className="mt-1.5 text-xs text-brand">
              Research will give extra depth to "{manualKeyword.trim()}"
              {webSearchEnabled ? ' — dedicated search queries will focus on this keyword' : ''}
            </p>
          )}
        </div>
      </section>

      {/* Section 4: what the scan starts with — and what it does not get */}
      <section className="mt-6">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">
          What this scan starts with
        </h2>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
            {(scanContext?.given || []).map((item) => (
              <div key={item.label} className="flex flex-col">
                <dt className="text-xs uppercase tracking-wide text-fg-subtle">{item.label}</dt>
                <dd className="text-sm text-fg">
                  {item.value}
                  <span className="ml-2 text-xs text-fg-subtle">({item.source})</span>
                </dd>
              </div>
            ))}
          </dl>

          {(scanContext?.not_given || []).map((item) => (
            <div key={item.label} className="mt-4 rounded-lg border border-sev-med/30 bg-sev-med/5 px-3 py-2">
              <p className="text-xs font-semibold text-fg">
                Not given to the scan — {item.label} ({item.value})
              </p>
              <p className="mt-1 text-xs text-fg-muted">{item.why}</p>
            </div>
          ))}

          <div className="mt-4">
            <label htmlFor="extra-context" className="text-sm font-semibold text-fg">
              Add what you already know
            </label>
            <p className="mb-2 text-xs text-fg-subtle">
              Goes to all three lenses as background. Prior findings, known issues, what
              changed last year, what the business told you.
            </p>
            <textarea
              id="extra-context"
              value={extraContext}
              onChange={(e) => setExtraContext(e.target.value)}
              maxLength={4000}
              rows={4}
              placeholder="e.g. Last year's audit found the onboarding checks were not evidenced. The team was reorganised in March."
              className="w-full resize-none rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-brand"
            />
            {extraContext.trim() && (
              <p className="mt-1 text-right text-xs text-fg-subtle">
                {extraContext.length} / 4000
              </p>
            )}
          </div>
        </div>
      </section>

      <div className="mt-6">
        <Button onClick={() => run.mutate()} disabled={run.isPending} className="w-full">
          {run.isPending ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Starting scan…</>
          ) : (
            'Run scan →'
          )}
        </Button>
        <p className="mt-2 text-center text-xs text-fg-subtle">
          You can proceed without documents. The scan will use built-in regulatory knowledge.
        </p>
      </div>
    </div>
  )
}
