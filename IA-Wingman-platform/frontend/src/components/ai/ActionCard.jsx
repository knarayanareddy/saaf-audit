import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, X, Plus, FolderPlus, PlayCircle, GitMerge, Flag, ArrowUpRight, Pencil } from 'lucide-react'
import { getAgentCatalog } from '../../api/agents'
import { useStore } from '../../store/useStore'
import { detailLines } from '../../lib/engagementEdit'
import { agentName, indexAgents } from '../../lib/agents'
import { entityLabel } from '../../lib/entities'

// Stage names come from the registry. The map that used to live here knew 15 of
// the 26 stages, so a card proposing scope, fieldwork, findings or any companion
// offered the auditor a raw key — 'racm_evidence_chase' — to accept or dismiss.

const STATUS_LABELS = {
  to_be_scheduled: 'To be scheduled', in_planning: 'In planning',
  in_fieldwork: 'In fieldwork', in_reporting: 'In reporting', closed: 'Closed',
}

// A proposed action from the AI. The human accepts or dismisses — the AI never executes.
export default function ActionCard({ action, onAccept, onDismiss }) {
  const { tool, input, status } = action
  // Shared with the rest of the app by react-query's cache; fetched once a session.
  const { data: catalog } = useQuery({ queryKey: ['agent-catalog'], queryFn: getAgentCatalog, staleTime: Infinity })
  const agents = useMemo(() => indexAgents(catalog?.agents), [catalog])
  const activeEngagement = useStore((s) => s.activeEngagement)

  let meta
  switch (tool) {
    case 'propose_create_engagement':
      meta = {
        icon: FolderPlus, label: 'Create engagement',
        lines: [input.name, `${entityLabel(input.entity)} · ${input.audit_type}`, input.summary].filter(Boolean),
      }
      break
    case 'propose_run_stage':
      meta = {
        icon: PlayCircle, label: 'Run stage',
        lines: [agentName(input.stage_key, agents), input.rationale].filter(Boolean),
      }
      break
    case 'propose_promote_finding':
      meta = {
        icon: Flag, label: 'Promote to finding',
        lines: [input.test_title || `Test ${input.test_id}`].filter(Boolean),
      }
      break
    case 'propose_update_engagement_status':
      meta = {
        icon: GitMerge, label: 'Update engagement status',
        lines: [STATUS_LABELS[input.new_status] || input.new_status, input.rationale].filter(Boolean),
      }
      break
    case 'propose_update_engagement_details': {
      const lines = detailLines(input, activeEngagement || {})
      meta = {
        icon: Pencil, label: 'Update engagement details',
        lines: [...(lines.length ? lines : ['Nothing would change']), input.rationale].filter(Boolean),
      }
      break
    }
    case 'propose_open_engagement':
      meta = {
        icon: ArrowUpRight, label: 'Open engagement',
        lines: [input.engagement_name, input.rationale].filter(Boolean),
      }
      break
    default: // propose_add_framework
      meta = {
        icon: Plus, label: 'Add framework',
        lines: [input.framework_name, input.applicability_rationale].filter(Boolean),
      }
  }

  const Icon = meta.icon

  return (
    <div className="mt-2 rounded-xl border border-brand/20 bg-brand-subtle/50 p-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-brand">
        <Icon size={13} /> {meta.label}
      </div>
      <div className="mt-1 space-y-0.5">
        {meta.lines.map((l, i) => (
          <div key={i} className={i === 0 ? 'text-sm font-medium text-fg' : 'text-xs text-fg-muted'}>
            {l}
          </div>
        ))}
      </div>
      {status === 'accepted' ? (
        <div className="mt-2 flex items-center gap-1 text-xs font-medium text-sev-low">
          <Check size={13} /> Done
        </div>
      ) : status === 'dismissed' ? (
        <div className="mt-2 text-xs text-fg-subtle">Dismissed</div>
      ) : status === 'expired' ? (
        <div className="mt-2 text-xs text-fg-subtle">From an earlier session — send a new message to act on this</div>
      ) : (
        <div className="mt-2 flex gap-2">
          <button
            onClick={onAccept}
            className="flex items-center gap-1 rounded-lg bg-sev-low/100 px-3 py-1 text-xs font-medium text-white hover:bg-sev-low/100"
          >
            <Check size={13} /> Accept
          </button>
          <button
            onClick={onDismiss}
            className="flex items-center gap-1 rounded-lg border border-line bg-white px-3 py-1 text-xs font-medium text-fg-muted hover:bg-surface-2"
          >
            <X size={13} /> Dismiss
          </button>
        </div>
      )}
    </div>
  )
}
