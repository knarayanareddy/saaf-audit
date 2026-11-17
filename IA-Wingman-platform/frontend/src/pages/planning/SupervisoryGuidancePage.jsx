import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Loader2, BookOpen, X, ExternalLink, Sparkles, Check } from 'lucide-react'
import { getEngagement } from '../../api/engagements'
import {
  getSupervisoryGuidance, analyseSupervisoryGuidance, getSupervisoryGuidanceStatus,
  deleteFramework,
} from '../../api/planning'
import Button from '../../components/ui/Button'
import JurisdictionSelect from '../../components/planning/JurisdictionSelect'
import { useStore } from '../../store/useStore'

const CONFIDENCE_STYLES = {
  high: 'bg-sev-low/10 text-sev-low',
  medium: 'bg-sev-med/10 text-sev-med',
  low: 'bg-surface-3 text-fg-muted',
}

const STAGE_LABELS = {
  searching_supervisors: 'Searching supervisory authority websites…',
  synthesising_guidance: 'Synthesising applicable guidance…',
}

function GuidanceCard({ gd, onRemove }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        {gd.is_primary && (
          <span className="rounded bg-brand-subtle px-2 py-0.5 text-[10px] font-semibold uppercase text-brand">
            Primary
          </span>
        )}
        {gd.source === 'guidance_analysed' && (
          <span className="rounded bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-violet-700">
            AI-analysed
          </span>
        )}
        {gd.framework_code && (
          <span className="rounded bg-surface-3 px-2 py-0.5 text-[10px] font-semibold uppercase text-fg-muted">
            {gd.framework_code}
          </span>
        )}
        {gd.jurisdiction && (
          <span className="rounded bg-surface-3 px-2 py-0.5 text-[10px] font-semibold uppercase text-fg-muted">
            {gd.jurisdiction}
          </span>
        )}
        {gd.confidence && (
          <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${CONFIDENCE_STYLES[gd.confidence] || 'bg-surface-3 text-fg-muted'}`}>
            {gd.confidence} confidence
          </span>
        )}
      </div>

      <div className="font-medium text-fg">{gd.framework_name}</div>

      {gd.guidance_type && (
        <div className="mt-1 inline-block rounded bg-brand-subtle/60 px-2 py-1 text-sm font-medium text-brand">
          {gd.guidance_type}
        </div>
      )}

      {gd.applicability_rationale && (
        <p className="mt-1.5 text-sm text-fg-muted">{gd.applicability_rationale}</p>
      )}

      <div className="mt-3 flex items-center justify-between">
        {gd.source_url ? (
          <a
            href={gd.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-brand hover:underline"
          >
            <ExternalLink size={12} /> Source
          </a>
        ) : (
          <span />
        )}
        <button
          onClick={() => onRemove(gd.id)}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-sev-high hover:bg-sev-high/10"
        >
          <X size={12} /> Remove
        </button>
      </div>
    </div>
  )
}

export default function SupervisoryGuidancePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  const { data: sg } = useQuery({
    queryKey: ['supervisory-guidance', id],
    queryFn: () => getSupervisoryGuidance(id),
  })
  const { data: analyseStatus } = useQuery({
    queryKey: ['sg-status', id],
    queryFn: () => getSupervisoryGuidanceStatus(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'running' ? 2000 : false
    },
  })

  // Refetch the guidance list whenever the run status changes (esp. into 'complete').
  const prevStatusRef = useRef(null)
  useEffect(() => {
    const status = analyseStatus?.status
    if (status && status !== prevStatusRef.current) {
      prevStatusRef.current = status
      qc.invalidateQueries({ queryKey: ['supervisory-guidance', id] })
    }
  }, [analyseStatus?.status, id, qc])

  const search = useMutation({
    mutationFn: () => analyseSupervisoryGuidance(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sg-status', id] }),
    onError: (err) => showToast(err.response?.data?.detail || 'Could not start search', 'error'),
  })

  // Auto-trigger the search ONCE on mount, only if never started — mirrors the
  // Laws & Regulations page. Deliberately does NOT auto-retry on 'failed' (that would
  // re-fire every poll cycle and burn AI + web-search budget); recovery is the manual
  // "Retry search" button.
  const autoTriggered = useRef(false)
  useEffect(() => {
    if (!analyseStatus || autoTriggered.current) return
    if (analyseStatus.status === 'not_started') {
      autoTriggered.current = true
      analyseSupervisoryGuidance(id)
        .then(() => qc.invalidateQueries({ queryKey: ['sg-status', id] }))
        .catch((err) => {
          autoTriggered.current = false
          showToast(err.response?.data?.detail || 'Could not start search', 'error')
        })
    }
  }, [analyseStatus?.status, id]) // eslint-disable-line react-hooks/exhaustive-deps

  const remove = useMutation({
    mutationFn: (fwId) => deleteFramework(fwId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['supervisory-guidance', id] })
      showToast('Guidance removed')
    },
  })

  const guidance = sg?.guidance || []
  const pollStatus = analyseStatus?.status || 'not_started'
  const isSearching = pollStatus === 'pending' || pollStatus === 'running'
  const stageLabel = STAGE_LABELS[analyseStatus?.stage] || 'Searching supervisory guidance…'

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
      <button
        onClick={() => navigate(`/engagements/${id}/planning`)}
        className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
      >
        <ArrowLeft size={16} /> Back to planning
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-h1 text-fg">Supervisory Guidance</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Applicable supervisory soft law — guidelines, policy rules, good practices and thematic
            reviews from the relevant authorities (DNB, AFM, NBB, FSMA, FCA, PRA, BdE, EBA, ECB, ESMA),
            per jurisdiction. Complements the binding law in Laws &amp; Regulations.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isSearching && (
            <div className="flex items-center gap-2 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-700">
              <Loader2 size={14} className="animate-spin" />
              {stageLabel}
            </div>
          )}
          {!isSearching && pollStatus === 'complete' && (
            <div className="flex items-center gap-1.5 rounded-lg bg-sev-low/10 px-3 py-2 text-sm text-sev-low">
              <Check size={14} /> Search complete
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-line bg-surface p-4">
        <JurisdictionSelect engagementId={id} />
      </div>

      <div className="mt-4 flex items-center justify-between rounded-xl border border-brand/20 bg-brand-faint p-4">
        <div className="min-w-0">
          <div className="text-sm font-medium text-fg">Search supervisory authority publications</div>
          <p className="mt-0.5 text-xs text-fg-muted">
            Starts automatically on first open — a live web search across the supervisors for the
            jurisdictions in scope. Re-run any time to refresh.
          </p>
        </div>
        <Button onClick={() => search.mutate()} disabled={isSearching || search.isPending}>
          {isSearching || search.isPending ? (
            <><Loader2 size={14} className="animate-spin" /> Searching…</>
          ) : (
            <><Sparkles size={14} /> {guidance.length > 0 ? 'Search again' : 'Search guidance'}</>
          )}
        </Button>
      </div>

      <div className="mt-6">
        {pollStatus === 'failed' && (
          <div className="mb-3 flex items-center justify-between rounded-xl bg-sev-high/10 px-4 py-3 text-sm text-sev-high">
            <span>Search failed.</span>
            <button
              onClick={() => search.mutate()}
              className="text-xs font-medium text-brand hover:underline"
            >
              Retry search →
            </button>
          </div>
        )}

        {guidance.length > 0 && (
          <p className="mb-3 text-sm text-fg-muted">
            {guidance.length} guidance document{guidance.length === 1 ? '' : 's'}
          </p>
        )}

        {isSearching && guidance.length === 0 && (
          <div className="border border-line flex items-center gap-3 rounded-xl bg-surface p-5 text-sm text-fg-muted">
            <Loader2 size={18} className="animate-spin text-brand" />
            {stageLabel} typically 20–40 seconds.
          </div>
        )}

        {!isSearching && guidance.length === 0 && (
          <div className="border border-line rounded-xl bg-surface p-6 text-center">
            <BookOpen size={28} className="mx-auto mb-2 text-brand-light" />
            <p className="text-sm text-fg-muted">
              No guidance yet. Click “Search guidance” above to find the supervisory publications
              applicable to this audit.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {guidance.map((gd) => (
            <GuidanceCard key={gd.id} gd={gd} onRemove={(fwId) => remove.mutate(fwId)} />
          ))}
        </div>
      </div>
    </div>
  )
}
