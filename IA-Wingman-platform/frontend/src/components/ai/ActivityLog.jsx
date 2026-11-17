import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Play, Check, Pencil, XCircle, AlertTriangle, History } from 'lucide-react'
import { getActivity, getAgentCatalog } from '../../api/agents'
import { agentIcon, agentName, indexAgents } from '../../lib/agents'
import { SourceChip, ConfidenceBadge } from '../ui/Provenance'
import EmptyState from '../ui/EmptyState'

// This map knew six verbs. Four of the seven actually written to the log —
// finding_ready, guide_ready, companion_ready, report_ready — were missing, so
// every one of them rendered as "ran" with a play icon. The provenance trail
// said an agent had started something when it had finished it.
const ACTION = {
  run: { icon: Play, label: 'started', cls: 'text-fg-muted' },
  review_ready: { icon: Check, label: 'has a draft ready for review', cls: 'text-brand' },
  finding_ready: { icon: Check, label: 'drafted a finding', cls: 'text-brand' },
  guide_ready: { icon: Check, label: 'produced an interview guide', cls: 'text-brand' },
  companion_ready: { icon: Check, label: 'wrote up the interview', cls: 'text-brand' },
  report_ready: { icon: Check, label: 'drafted the report', cls: 'text-brand' },
  accept: { icon: Check, label: 'accepted', cls: 'text-sev-low' },
  edit: { icon: Pencil, label: 'edited', cls: 'text-sev-med' },
  dismiss: { icon: XCircle, label: 'dismissed', cls: 'text-fg-subtle' },
  error: { icon: AlertTriangle, label: 'failed', cls: 'text-sev-high' },
}

// Names come from the registry now. This map held five keys, and only two of
// them were ever written to the log; the rest of the trail showed the auditor
// raw snake_case — 'finding_drafter', 'report_drafter', 'peer_review'.

function timeAgo(iso) {
  if (!iso) return ''
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  const s = Math.round((Date.now() - d.getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

export default function ActivityLog({ engagementId }) {
  const { data: items = [] } = useQuery({
    queryKey: ['activity', engagementId],
    queryFn: () => getActivity(engagementId),
    refetchInterval: 8000,
  })
  // The catalog never changes within a session and costs nothing to serve.
  const { data: catalog } = useQuery({ queryKey: ['agent-catalog'], queryFn: getAgentCatalog, staleTime: Infinity })
  const index = useMemo(() => indexAgents(catalog?.agents), [catalog])

  if (items.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No AI activity yet"
        description="Every agent run and human decision is logged here — the provenance trail for this engagement."
      />
    )
  }

  return (
    <ol className="relative space-y-4 border-l border-line pl-5">
      {items.map((it) => {
        const a = ACTION[it.action] || ACTION.run
        const Icon = a.icon
        const agent = index[it.agent]
        const AgentIcon = agent ? agentIcon(agent.icon) : null
        const isHuman = it.actor && it.actor !== 'AI'
        return (
          <li key={it.id} className="relative">
            <span className="absolute -left-[27px] flex h-5 w-5 items-center justify-center rounded-full border border-line bg-surface">
              <Icon size={11} className={a.cls} />
            </span>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
              <span className="inline-flex items-center gap-1.5 font-medium text-fg">
                {AgentIcon && <AgentIcon size={13} className="shrink-0 text-fg-muted" />}
                {agentName(it.agent, index)}
              </span>
              <span className="text-fg-muted">{a.label}</span>
              {isHuman && <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[11px] text-fg-muted">by {it.actor}</span>}
              <span className="text-xs text-fg-subtle">· {timeAgo(it.created_at)}</span>
            </div>
            {it.summary && <p className="mt-0.5 text-sm text-fg-muted">{it.summary}</p>}
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              {(it.sources || []).map((s, i) => <SourceChip key={i} type={s.type} />)}
              {it.confidence && <ConfidenceBadge level={it.confidence} />}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
