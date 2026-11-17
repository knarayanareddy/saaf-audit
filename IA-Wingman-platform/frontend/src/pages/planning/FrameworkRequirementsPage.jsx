import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Loader2, ListChecks, Plus, X, ExternalLink, Sparkles, Check,
} from 'lucide-react'
import { getEngagement } from '../../api/engagements'
import {
  getFrameworkLibrary, addFramework, deleteFramework,
  getFrameworkRequirements, analyseFrameworkRequirements, getFrameworkRequirementsStatus,
  patchRequirementItem, acceptFrameworkRequirements,
  generateFwScope, publishFwScope,
} from '../../api/planning'
import Button from '../../components/ui/Button'
import JurisdictionSelect from '../../components/planning/JurisdictionSelect'
import { useStore } from '../../store/useStore'

const CONFIDENCE_STYLES = {
  high: 'bg-sev-low/10 text-sev-low',
  medium: 'bg-sev-med/10 text-sev-med',
  low: 'bg-surface-3 text-fg-muted',
}

const SCOPE_TYPE_STYLES = {
  in_scope: 'bg-sev-low/10 text-sev-low',
  out_of_scope: 'bg-sev-high/10 text-sev-high',
  key_question: 'bg-blue-100 text-blue-700',
}

const TEST_APPROACH_TYPES = {
  Walkthrough: 'bg-blue-50 text-blue-700',
  Sample: 'bg-sev-med/10 text-sev-med',
  Inspection: 'bg-violet-50 text-violet-700',
  Inquiry: 'bg-surface-3 text-fg-muted',
  'Re-performance': 'bg-sev-high/10 text-sev-high',
  Observation: 'bg-sev-low/10 text-sev-low',
}

const STAGE_LABELS = {
  identifying_frameworks: 'Identifying applicable frameworks…',
  deriving_requirements: 'Deriving control requirements from accepted frameworks…',
}

function approachBadge(approach) {
  const key = Object.keys(TEST_APPROACH_TYPES).find((k) =>
    approach?.toLowerCase().includes(k.toLowerCase())
  )
  return TEST_APPROACH_TYPES[key] || 'bg-surface-3 text-fg-muted'
}

function RequirementCard({ item, onPatch }) {
  const included = item.is_included !== false

  return (
    <div className={`rounded-lg border border-line bg-surface p-4 transition-opacity ${included ? '' : 'opacity-50'}`}>
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={included}
          onChange={() => onPatch(item.id, { is_included: !included })}
          className="mt-1 h-4 w-4 rounded border-line-strong accent-brand"
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-fg">{item.what_it_requires}</p>

          <div className="mt-2 rounded-lg bg-sev-low/10 px-3 py-2">
            <div className="mb-0.5 text-[10px] font-semibold uppercase text-sev-low">Control objective</div>
            <p className="text-sm text-sev-low">{item.control_objective}</p>
          </div>

          {item.test_approach && (
            <div className="mt-1.5 flex items-start gap-2">
              <span className={`mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${approachBadge(item.test_approach)}`}>
                {item.test_approach.split(' ')[0]}
              </span>
              <p className="text-xs text-fg-muted">{item.test_approach}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function FrameworkCard({ fw, isAnalysing, onRemove, onPatchRequirement }) {
  const requirements = fw.requirements || []
  const included = requirements.filter((r) => r.is_included !== false)

  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        {fw.is_primary && (
          <span className="rounded bg-brand-subtle px-2 py-0.5 text-[10px] font-semibold uppercase text-brand">
            Primary
          </span>
        )}
        {fw.source === 'auto_analysed' && (
          <span className="rounded bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-violet-700">
            AI-analysed
          </span>
        )}
        {fw.source === 'ai_suggested' && (
          <span className="rounded bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-violet-700">
            AI-suggested
          </span>
        )}
        {fw.jurisdiction && (
          <span className="rounded bg-surface-3 px-2 py-0.5 text-[10px] font-semibold uppercase text-fg-muted">
            {fw.jurisdiction}
          </span>
        )}
        {fw.confidence && (
          <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${CONFIDENCE_STYLES[fw.confidence] || 'bg-surface-3 text-fg-muted'}`}>
            {fw.confidence} confidence
          </span>
        )}
      </div>

      <div className="font-medium text-fg">{fw.framework_name}</div>

      {fw.specific_provision && (
        <div className="mt-1 rounded bg-brand-subtle/60 px-2 py-1 text-sm font-medium text-brand">
          {fw.specific_provision}
        </div>
      )}

      {fw.applicability_rationale && (
        <p className="mt-1.5 text-sm text-fg-muted">{fw.applicability_rationale}</p>
      )}

      <div className="mt-3 flex items-center justify-between">
        {fw.source_url ? (
          <a
            href={fw.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-brand hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={12} /> Source
          </a>
        ) : (
          <span />
        )}
        <button
          onClick={() => onRemove(fw.id)}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-sev-high hover:bg-sev-high/10"
        >
          <X size={12} /> Remove
        </button>
      </div>

      {requirements.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-line pt-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
            Requirements ({included.length}/{requirements.length} included)
          </div>
          {requirements.map((item) => (
            <RequirementCard key={item.id} item={item} onPatch={onPatchRequirement} />
          ))}
        </div>
      )}

      {requirements.length === 0 && isAnalysing && (
        <div className="mt-3 flex items-center gap-2 border-t border-line pt-3 text-xs text-fg-subtle">
          <Loader2 size={12} className="animate-spin" /> Deriving requirements…
        </div>
      )}
    </div>
  )
}

export default function FrameworkRequirementsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [selected, setSelected] = useState('')
  const [scopeVisible, setScopeVisible] = useState(false)
  const [scopeItems, setScopeItems] = useState(null)
  const [checkedScope, setCheckedScope] = useState({})

  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  const { data: fr } = useQuery({
    queryKey: ['framework-requirements', id],
    queryFn: () => getFrameworkRequirements(id),
  })
  const { data: library = [] } = useQuery({
    queryKey: ['fw-library', eng?.entity],
    queryFn: () => getFrameworkLibrary(eng?.entity),
    enabled: !!eng,
  })
  const { data: analyseStatus } = useQuery({
    queryKey: ['fw-requirements-status', id],
    queryFn: () => getFrameworkRequirementsStatus(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'running' ? 2000 : false
    },
  })

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['framework-requirements', id] })
    qc.invalidateQueries({ queryKey: ['fw-requirements-status', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  // Auto-trigger analysis ONCE on mount, only if never started.
  // Deliberately does NOT auto-retry on 'failed' — a failing analysis (e.g. bad API
  // key or transient error) would otherwise re-fire every poll cycle in a tight loop,
  // burning API credits. Recovery from 'failed' is via the manual "Retry analysis" button.
  const autoTriggered = useRef(false)
  useEffect(() => {
    if (!analyseStatus || autoTriggered.current) return
    if (analyseStatus.status === 'not_started') {
      autoTriggered.current = true
      analyseFrameworkRequirements(id)
        .then(() => qc.invalidateQueries({ queryKey: ['fw-requirements-status', id] }))
        .catch((err) => {
          autoTriggered.current = false
          showToast(err.response?.data?.detail || 'Could not start analysis', 'error')
        })
    }
  }, [analyseStatus?.status, id]) // eslint-disable-line react-hooks/exhaustive-deps

  const retryAnalysis = () =>
    analyseFrameworkRequirements(id)
      .then(() => qc.invalidateQueries({ queryKey: ['fw-requirements-status', id] }))
      .catch((err) => showToast(err.response?.data?.detail || 'Could not start analysis', 'error'))

  // The frameworks/requirements payload has its own query (not polled) — without this,
  // the page would keep showing "no frameworks yet" even after analysis finishes, since
  // only the lightweight status query above is polled. Refetch on every status change,
  // most importantly the transition into 'complete'.
  const prevStatusRef = useRef(null)
  useEffect(() => {
    const status = analyseStatus?.status
    if (status && status !== prevStatusRef.current) {
      prevStatusRef.current = status
      qc.invalidateQueries({ queryKey: ['framework-requirements', id] })
    }
  }, [analyseStatus?.status, id, qc])

  const remove = useMutation({
    mutationFn: (fwId) => deleteFramework(fwId),
    onSuccess: () => { invalidate(); showToast('Framework removed') },
  })

  const add = useMutation({
    mutationFn: () => {
      const lib = library.find((l) => l.code === selected)
      return addFramework(id, { framework_code: lib.code, framework_name: lib.name, is_primary: false })
    },
    onSuccess: () => { invalidate(); setSelected(''); showToast('Framework added') },
  })

  const patchMutation = useMutation({
    mutationFn: ({ itemId, payload }) => patchRequirementItem(id, itemId, payload),
    onSuccess: (_data, { itemId, payload }) =>
      qc.setQueryData(['framework-requirements', id], (old) => {
        if (!old) return old
        return {
          ...old,
          frameworks: old.frameworks.map((fw) => ({
            ...fw,
            requirements: (fw.requirements || []).map((r) => (r.id === itemId ? { ...r, ...payload } : r)),
          })),
        }
      }),
  })

  const acceptMutation = useMutation({
    mutationFn: () => acceptFrameworkRequirements(id),
    onSuccess: () => { showToast('Frameworks & requirements saved'); invalidate() },
  })

  const generateScope = useMutation({
    mutationFn: () => generateFwScope(id),
    onSuccess: (data) => {
      setScopeItems(data)
      setScopeVisible(true)
      // Pre-check all items
      const initial = {}
      ;[...data.scope_items, ...data.key_questions].forEach((_, i) => {
        initial[i] = true
      })
      setCheckedScope(initial)
    },
  })

  const publish = useMutation({
    mutationFn: () => {
      const selected_scope = (scopeItems?.scope_items || []).filter((_, i) => checkedScope[i])
      const selected_q = (scopeItems?.key_questions || []).filter((_, i) =>
        checkedScope[(scopeItems?.scope_items || []).length + i]
      )
      return publishFwScope(id, { scope_items: selected_scope, key_questions: selected_q })
    },
    onSuccess: (data) => {
      showToast(`Published ${data.items_added} scope items and ${data.questions_added} questions`)
      setScopeItems(null)
      setScopeVisible(false)
    },
  })

  const frameworks = fr?.frameworks || []
  const frStatus = fr?.status || 'not_started'
  const allRequirements = frameworks.flatMap((fw) => fw.requirements || [])
  const includedRequirements = allRequirements.filter((r) => r.is_included !== false)

  const pollStatus = analyseStatus?.status || 'not_started'
  const isAnalysing = pollStatus === 'pending' || pollStatus === 'running'
  const stageLabel = STAGE_LABELS[analyseStatus?.stage] || 'Analysing regulatory landscape and requirements…'

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
      <button
        onClick={() => navigate(`/engagements/${id}/planning`)}
        className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
      >
        <ArrowLeft size={16} /> Back to planning
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-h1 text-fg">Laws & Regulation selection</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Applicable laws & regulations for this audit, per jurisdiction, with the specific control requirements derived from each.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {frStatus === 'agreed' && (
            <div className="flex items-center gap-1 rounded-lg bg-sev-low/10 px-3 py-2 text-sm text-sev-low">
              <Check size={14} /> Agreed
            </div>
          )}
          {isAnalysing && (
            <div className="flex items-center gap-2 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-700">
              <Loader2 size={14} className="animate-spin" />
              {stageLabel}
            </div>
          )}
          {!isAnalysing && pollStatus === 'complete' && frStatus !== 'agreed' && (
            <div className="flex items-center gap-1.5 rounded-lg bg-sev-low/10 px-3 py-2 text-sm text-sev-low">
              <Check size={14} /> Analysis complete
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-line bg-surface p-4">
        <JurisdictionSelect engagementId={id} />
      </div>

      {/* Framework + requirements list */}
      <div className="mt-6">
        {pollStatus === 'failed' && (
          <div className="mb-3 flex items-center justify-between rounded-xl bg-sev-high/10 px-4 py-3 text-sm text-sev-high">
            <span>Analysis failed.</span>
            <button onClick={retryAnalysis} className="text-xs font-medium text-brand hover:underline">
              Retry analysis →
            </button>
          </div>
        )}

        {(frStatus === 'draft_ready' || frStatus === 'agreed') && frameworks.length > 0 && (
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-fg-muted">
              {frameworks.length} framework{frameworks.length === 1 ? '' : 's'} · {includedRequirements.length}/{allRequirements.length} requirements included
              {frStatus === 'agreed' && <span className="ml-2 text-sev-low font-medium">· Saved</span>}
            </p>
            {frStatus === 'draft_ready' && (
              <Button
                onClick={() => acceptMutation.mutate()}
                disabled={acceptMutation.isPending || includedRequirements.length === 0}
              >
                <Check size={14} />
                {acceptMutation.isPending
                  ? 'Saving…'
                  : `Accept ${frameworks.length} frameworks & ${includedRequirements.length} requirements`}
              </Button>
            )}
          </div>
        )}

        {isAnalysing && frameworks.length === 0 && (
          <div className="border border-line flex items-center gap-3 rounded-xl bg-surface p-5 text-sm text-fg-muted">
            <Loader2 size={18} className="animate-spin text-brand" />
            {stageLabel} typically 30–60 seconds.
          </div>
        )}

        {!isAnalysing && frameworks.length === 0 && (
          <div className="border border-line rounded-xl bg-surface p-6 text-center">
            <ListChecks size={28} className="mx-auto mb-2 text-brand-light" />
            <p className="text-sm text-fg-muted">
              No frameworks yet. Analysis will start automatically — or add one manually above.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {frameworks.map((fw) => (
            <FrameworkCard
              key={fw.id}
              fw={fw}
              isAnalysing={isAnalysing}
              onRemove={(fwId) => remove.mutate(fwId)}
              onPatchRequirement={(itemId, payload) => patchMutation.mutate({ itemId, payload })}
            />
          ))}
        </div>
      </div>

      {/* Scope & Objectives contribution */}
      {frameworks.length > 0 && (
        <div className="mt-10 rounded-xl border border-line bg-surface-3 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-fg">Scope &amp; Objectives contribution</h2>
            <Button
              variant="secondary"
              onClick={() => generateScope.mutate()}
              disabled={generateScope.isPending}
            >
              {generateScope.isPending ? (
                <><Loader2 size={14} className="animate-spin" /> Generating…</>
              ) : (
                <><Sparkles size={14} /> Generate</>
              )}
            </Button>
          </div>
          <p className="mt-1 text-xs text-fg-muted">
            AI derives scope items and key audit questions from the confirmed frameworks above.
          </p>

          {scopeVisible && scopeItems && (
            <div className="mt-4 space-y-2">
              {/* Scope items */}
              {scopeItems.scope_items?.map((item, i) => (
                <label key={i} className="flex cursor-pointer items-start gap-2 rounded-lg bg-surface p-3 shadow-sm">
                  <input
                    type="checkbox"
                    className="mt-0.5 accent-brand"
                    checked={!!checkedScope[i]}
                    onChange={(e) => setCheckedScope((prev) => ({ ...prev, [i]: e.target.checked }))}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SCOPE_TYPE_STYLES[item.item_type] || 'bg-surface-3 text-fg-muted'}`}>
                        {item.item_type === 'in_scope' ? 'In scope' : 'Out of scope'}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-fg">{item.description}</div>
                    {item.rationale && <div className="text-xs text-fg-muted mt-0.5">{item.rationale}</div>}
                  </div>
                </label>
              ))}

              {/* Key questions */}
              {scopeItems.key_questions?.map((q, i) => {
                const idx = (scopeItems.scope_items?.length || 0) + i
                return (
                  <label key={`q-${i}`} className="flex cursor-pointer items-start gap-2 rounded-lg bg-surface p-3 shadow-sm">
                    <input
                      type="checkbox"
                      className="mt-0.5 accent-brand"
                      checked={!!checkedScope[idx]}
                      onChange={(e) => setCheckedScope((prev) => ({ ...prev, [idx]: e.target.checked }))}
                    />
                    <div className="flex-1">
                      <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-blue-700">
                        Key Q
                      </span>
                      <div className="mt-0.5 text-sm font-medium text-fg">{q.question_text}</div>
                      {q.regulatory_basis && <div className="text-xs text-fg-muted">{q.regulatory_basis}</div>}
                    </div>
                  </label>
                )
              })}

              <div className="mt-3 flex items-center justify-between">
                <button
                  onClick={() => { setScopeItems(null); setScopeVisible(false) }}
                  className="text-xs text-fg-subtle hover:text-fg-muted"
                >
                  Dismiss
                </button>
                <Button onClick={() => publish.mutate()} disabled={publish.isPending}>
                  {publish.isPending ? (
                    <><Loader2 size={14} className="animate-spin" /> Publishing…</>
                  ) : (
                    <>Publish {Object.values(checkedScope).filter(Boolean).length} → Scope &amp; Objectives</>
                  )}
                </Button>
              </div>
            </div>
          )}

          {!scopeVisible && (
            <p className="mt-2 text-xs text-fg-subtle">
              Click Generate to derive scope items from the frameworks above.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
