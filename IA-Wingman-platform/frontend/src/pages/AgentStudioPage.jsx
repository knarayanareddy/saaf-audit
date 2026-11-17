import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Workflow, Check, Lock, ArrowRight, Loader2, CircleDot, XCircle,
  Sparkles, ChevronRight, Activity, Inbox, ExternalLink, X, AlertTriangle,
  Pause, Play, Lightbulb,
} from 'lucide-react'
import { getEngagement } from '../api/engagements'
import { getAgentRuns, getAgentPack, getAgentSpend } from '../api/agents'
import { getCopilotTasks, patchCopilotTask, setCopilotAutonomy } from '../api/ai'
import { useStore } from '../store/useStore'
import PageContainer from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import { EntityBadge } from '../components/ui/Badge'
import { Card, SectionHeading } from '../components/ui/Card'
import { SummaryCard } from '../components/ui/ReadableOutput'

// ── Planning pack — gated cascade ──────────────────────────────────────────────
const STAGE_STATUS = {
  complete: { icon: Check, ring: 'bg-sev-low/12 ring-sev-low/30 text-sev-low', line: 'bg-sev-low/40' },
  in_progress: { icon: Loader2, ring: 'bg-brand/12 ring-brand/30 text-brand', line: 'bg-brand/40', spin: true },
  available: { icon: ArrowRight, ring: 'bg-sev-med/12 ring-sev-med/30 text-sev-med', line: 'bg-line' },
  locked: { icon: Lock, ring: 'bg-surface-3 ring-line text-fg-subtle', line: 'bg-line' },
}

function PlanningPack({ engagementId }) {
  const navigate = useNavigate()
  const { data } = useQuery({
    queryKey: ['agent-pack', engagementId],
    queryFn: () => getAgentPack(engagementId),
    refetchInterval: (q) => (q.state.data?.stages?.some((s) => s.status === 'in_progress') ? 3000 : false),
  })
  if (!data) return <div className="h-40 animate-pulse rounded-xl bg-surface-3" />

  return (
    <div className="space-y-4">
      <SummaryCard title="Lifecycle cascade" icon={Workflow}>{data.summary}</SummaryCard>
      <ol className="relative">
        {data.stages.map((s, i) => {
          const meta = STAGE_STATUS[s.status] || STAGE_STATUS.locked
          const Icon = meta.icon
          const clickable = s.status !== 'locked'
          const isNext = data.next_gate === s.key
          const last = i === data.stages.length - 1
          return (
            <li key={s.key} className="relative flex gap-4 pb-4">
              {!last && <span className={`absolute left-[18px] top-9 h-[calc(100%-1rem)] w-0.5 ${meta.line}`} />}
              <span className={`z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ring-1 ring-inset ${meta.ring}`}>
                <Icon size={16} className={meta.spin ? 'animate-spin' : ''} />
              </span>
              <button
                disabled={!clickable}
                onClick={() => navigate(`/engagements/${engagementId}/${s.base ? `${s.base}/` : ''}${s.route}`)}
                className={`group flex min-w-0 flex-1 items-center justify-between gap-3 rounded-xl border p-3 text-left transition ${
                  isNext ? 'border-sev-med/40 bg-sev-med/5' : 'border-line bg-surface'
                } ${clickable ? 'hover:border-brand/40 hover:bg-surface-3' : 'cursor-not-allowed opacity-70'}`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-sm font-semibold text-fg">
                    {s.label}
                    {isNext && <span className="rounded-full bg-sev-med/15 px-1.5 py-0.5 text-[11px] font-semibold text-sev-med">Next gate</span>}
                  </div>
                  <div className="mt-0.5 text-xs text-fg-muted">
                    <span className="text-fg-subtle">{s.agent}</span> · {s.detail}
                  </div>
                </div>
                {clickable && <ChevronRight size={16} className="shrink-0 text-fg-subtle transition group-hover:text-brand" />}
              </button>
            </li>
          )
        })}
      </ol>
      <p className="text-xs text-fg-subtle">
        Each gate is opened by you — the cascade never auto-runs. Locked stages wait on their predecessor.
      </p>
    </div>
  )
}

// ── Live run-graph ──────────────────────────────────────────────────────────────
const RUN_STATUS = {
  complete: { icon: Check, cls: 'text-sev-low bg-sev-low/12 ring-sev-low/25' },
  running: { icon: Loader2, cls: 'text-brand bg-brand/12 ring-brand/25', spin: true },
  waiting: { icon: CircleDot, cls: 'text-sev-med bg-sev-med/12 ring-sev-med/25' },
  pending: { icon: CircleDot, cls: 'text-fg-subtle bg-surface-3 ring-line' },
  failed: { icon: XCircle, cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25' },
}

const AGENT_LABELS = {
  regulatory: 'Regulatory Intelligence', policy: 'Policy & Framework', interview: 'Interview Guide',
  lens1: 'Lens 1 · Regulatory', lens2: 'Lens 2 · Supervisory', lens3: 'Lens 3 · Society',
  governance_assessor: 'Governance Assessor', data_analysis: 'Data Analysis',
}

function RunGraph({ engagementId }) {
  const { data: runs } = useQuery({
    queryKey: ['agent-runs', engagementId],
    queryFn: () => getAgentRuns(engagementId),
    refetchInterval: (q) => (q.state.data?.some((r) => ['running', 'pending', 'waiting'].includes(r.status)) ? 2500 : false),
  })
  if (!runs) return <div className="h-32 animate-pulse rounded-xl bg-surface-3" />
  if (runs.length === 0) {
    return (
      <p className="text-sm text-fg-muted">
        No agent runs yet. Start Topic Intelligence to see live orchestration here.
      </p>
    )
  }

  const active = runs.filter((r) => ['running', 'pending', 'waiting'].includes(r.status)).length
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-fg-muted">
        <Activity size={13} className={active ? 'text-brand' : 'text-fg-subtle'} />
        {active ? `${active} agent(s) working…` : `${runs.length} run(s) in history`}
      </div>
      <ul className="space-y-2">
        {runs.map((r) => {
          const meta = RUN_STATUS[r.status] || RUN_STATUS.pending
          const Icon = meta.icon
          return (
            <li key={r.id} className="flex items-center gap-3 rounded-xl border border-line bg-surface p-3">
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset ${meta.cls}`}>
                <Icon size={15} className={meta.spin ? 'animate-spin' : ''} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-fg">{AGENT_LABELS[r.agent_type] || r.agent_type}</div>
                {r.input_summary && <div className="truncate text-xs text-fg-muted">{r.input_summary}</div>}
              </div>
              <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{r.status}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

// ── Ready for review — the auto-run batch ────────────────────────────────────
function ReadyForReview({ engagementId }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: pack } = useQuery({ queryKey: ['agent-pack', engagementId], queryFn: () => getAgentPack(engagementId) })
  const { data: tasks } = useQuery({
    queryKey: ['copilot-tasks', engagementId, 'ready_for_review'],
    queryFn: () => getCopilotTasks(engagementId, 'ready_for_review'),
    refetchInterval: 5000,
  })
  const stageMeta = Object.fromEntries((pack?.stages || []).map((s) => [s.key, s]))

  const act = async (taskId, status) => {
    await patchCopilotTask(taskId, status)
    qc.invalidateQueries({ queryKey: ['copilot-tasks', engagementId] })
  }

  if (!tasks) return <div className="h-24 animate-pulse rounded-xl bg-surface-3" />
  if (tasks.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-fg-muted">
        <Inbox size={15} className="text-fg-subtle" /> Nothing waiting for review — the copilot posts auto-drafted stages here.
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {tasks.map((t) => {
        // Item-level tasks (a single finding/interview session) resolve via
        // the label/route the backend already attached — they have no
        // STAGE_GRAPH entry of their own to look up.
        const meta = t.item_id
          ? { label: t.item_label, detail: '', base: t.item_base, route: t.item_route }
          : stageMeta[t.stage_key] || { label: t.stage_key, detail: '', base: '', route: '' }
        return (
          <li key={t.id} className="flex items-center justify-between gap-3 rounded-xl border border-line bg-surface p-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-medium text-fg">
                {meta.label}
                {t.flagged && (
                  <span className="flex items-center gap-1 rounded-full bg-sev-med/15 px-1.5 py-0.5 text-[11px] font-semibold text-sev-med">
                    <AlertTriangle size={11} /> Flagged — verify before relying on this
                  </span>
                )}
              </div>
              <div className="mt-0.5 truncate text-xs text-fg-muted">{meta.detail}</div>
              {t.rationale && (
                <div className="mt-0.5 flex items-center gap-1 text-[11px] text-fg-subtle italic" title={t.rationale}>
                  <Lightbulb size={11} className="shrink-0 not-italic" /> <span className="truncate">{t.rationale}</span>
                </div>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <button
                onClick={() => navigate(`/engagements/${engagementId}/${meta.base ? `${meta.base}/` : ''}${meta.route}`)}
                className="flex items-center gap-1 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-fg transition hover:bg-surface-3"
              >
                <ExternalLink size={13} /> Open
              </button>
              <button
                onClick={() => act(t.id, 'reviewed')}
                className="flex items-center gap-1 rounded-lg bg-sev-low/100 px-2.5 py-1.5 text-xs font-medium text-white transition hover:bg-sev-low/100"
              >
                <Check size={13} /> Accept
              </button>
              <button
                onClick={() => act(t.id, 'dismissed')}
                className="flex items-center gap-1 rounded-lg border border-line px-2 py-1.5 text-xs font-medium text-fg-subtle transition hover:bg-surface-3"
                aria-label="Dismiss"
              >
                <X size={13} />
              </button>
            </div>
          </li>
        )
      })}
    </ul>
  )
}

// ── What this engagement has spent ───────────────────────────────────────────
// The budget used to be "twenty auto-started tasks", which told an auditor
// nothing: twenty runs on the judge tier and twenty title suggestions are not
// the same commitment. This reads the ledger, so it survives a refresh and
// covers every call — including the ones that never created an agent run.
function money(value) {
  if (value == null) return 'not priced'
  return value < 0.01 ? `$${value.toFixed(4)}` : `$${value.toFixed(2)}`
}

function Spend({ engagementId }) {
  const { data } = useQuery({
    queryKey: ['agent-spend', engagementId],
    queryFn: () => getAgentSpend(engagementId),
    refetchInterval: 15000,
  })
  if (!data) return null
  const { spend, budget_usd: budget, recent } = data
  if (!spend.calls) return null

  const pct = budget ? Math.min(100, Math.round((spend.total_usd / budget) * 100)) : 0
  const tiers = Object.entries(spend.by_tier || {})

  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-caption text-fg-subtle">Spent on this engagement</span>
        <span className="text-sm font-semibold tabular-nums text-fg">
          {money(spend.total_usd)}
          {budget ? <span className="font-normal text-fg-subtle"> of {money(budget)}</span> : null}
        </span>
      </div>
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-3">
        <div className="h-full rounded-full bg-brand" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-fg-subtle">
        <span>{spend.calls} call{spend.calls === 1 ? '' : 's'}</span>
        {spend.failed > 0 && <span className="text-sev-med">{spend.failed} failed</span>}
        {tiers.map(([tier, amount]) => <span key={tier}>{tier} {money(amount)}</span>)}
        {spend.thinking_tokens > 0 && <span>{spend.thinking_tokens.toLocaleString()} reasoning tokens</span>}
        {/* Stated, not folded into the total: an unpriced call is an unknown
            amount, not a free one. */}
        {spend.unpriced_calls > 0 && (
          <span title="These models have no price configured — see services/model_tiers.py">
            {spend.unpriced_calls} not priced
          </span>
        )}
      </div>
      {recent?.length > 0 && (
        <ul className="mt-2 space-y-1">
          {recent.slice(0, 4).map((c) => (
            <li key={c.id} className="flex items-baseline justify-between gap-2 text-[11px] text-fg-subtle">
              <span className="truncate">
                {!c.ok && <span className="text-sev-high">failed · </span>}
                {c.agent || c.schema || 'agent'} · {c.tier || 'draft'}
                {(c.thinking_tokens > 0 || c.reasoned) && ' · reasoned'}
                {c.repaired && ' · corrected'}
              </span>
              <span className="shrink-0 tabular-nums">
                {(c.duration_ms / 1000).toFixed(1)}s · {money(c.cost_usd)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Autonomy pause toggle ─────────────────────────────────────────────────────
function AutonomyToggle({ engagementId, paused }) {
  const qc = useQueryClient()
  const toggle = async () => {
    await setCopilotAutonomy(engagementId, !paused)
    qc.invalidateQueries({ queryKey: ['engagement', engagementId] })
  }
  return (
    <button
      onClick={toggle}
      title={paused ? 'Autonomy is paused — click to resume auto-fire' : 'Autonomy is active — click to pause auto-fire'}
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition ${
        paused
          ? 'bg-sev-med/12 text-sev-med hover:bg-sev-med/20'
          : 'bg-sev-low/12 text-sev-low hover:bg-sev-low/20'
      }`}
    >
      {paused ? <Play size={12} /> : <Pause size={12} />}
      {paused ? 'Autonomy paused' : 'Autonomy active'}
    </button>
  )
}

export default function AgentStudioPage() {
  const { id } = useParams()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  useEffect(() => { if (eng) setActiveEngagement(eng) }, [eng, setActiveEngagement])

  return (
    <PageContainer>
      <PageHeader
        back={{ to: `/engagements/${id}/planning`, label: 'Planning' }}
        badges={eng && <EntityBadge entity={eng.entity} />}
        title="Agent Studio"
        subtitle={eng?.name}
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-fg">
              <Workflow size={16} className="text-brand" /> Lifecycle pack
            </div>
            {eng && <AutonomyToggle engagementId={id} paused={eng.copilot_autonomy_paused} />}
          </div>
          <PlanningPack engagementId={id} />
          <Spend engagementId={id} />
        </Card>
        <div>
          <SectionHeading>Live agent orchestration</SectionHeading>
          <Card className="mt-3 p-5"><RunGraph engagementId={id} /></Card>
        </div>
      </div>
      <div className="mt-6">
        <SectionHeading>Ready for review</SectionHeading>
        <Card className="mt-3 p-5"><ReadyForReview engagementId={id} /></Card>
      </div>
    </PageContainer>
  )
}
