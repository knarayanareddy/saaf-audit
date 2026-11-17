import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, X } from 'lucide-react'
import { getAgentCatalog, getAgentSpend } from '../api/agents'
import { useStore } from '../store/useStore'
import { agentIcon, kindMeta } from '../lib/agents'
import PageContainer from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import Section from '../components/ui/Section'
import Segmented from '../components/ui/Segmented'
import Toolbar from '../components/ui/Toolbar'
import Tooltip from '../components/ui/Tooltip'

// The roster. Until now there was no screen that answered "show me your agents":
// the Agent Studio lives per engagement, behind the Planning hub, and the
// workflow map draws all twenty-six nodes with the same circle.
//
// It is deterministic and costs nothing — the catalog is the registry, not a
// query — so it is always available, with or without an engagement open.

const PHASES = [
  { key: 'planning', label: 'Planning' },
  { key: 'racm', label: 'Risk & Control' },
  { key: 'fieldwork', label: 'Fieldwork' },
  { key: 'reporting', label: 'Reporting' },
  { key: 'quality', label: 'Quality' },
]

const TIER_NOTE = {
  judge: 'Runs on the strongest model, with room to reason — its output is the judgement.',
  draft: 'Drafts something you read line by line before it counts.',
  quick: 'A short answer where being wrong is cheap and obvious.',
  none: 'Never calls a model.',
}

function Row({ agent, active, onOpen, onSelect }) {
  const Icon = agentIcon(agent.icon)
  const kind = kindMeta(agent.kind)
  const KindIcon = kind.icon
  return (
    <button
      type="button"
      onClick={() => onSelect(agent)}
      className={`group flex w-full items-start gap-3 border-b border-line-subtle px-3 py-2.5 text-left transition-colors duration-150 last:border-0 hover:bg-surface-2 focus:outline-none focus-visible:shadow-ring ${
        active ? 'bg-surface-2' : ''
      }`}
    >
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-3 text-fg-muted">
        <Icon size={14} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-sm font-medium text-fg">{agent.name}</span>
          <Tooltip label={kind.hint} width="16rem">
            <span className={`inline-flex items-center gap-1 text-[11px] ${kind.cls}`}>
              <KindIcon size={10} /> {kind.label}
            </span>
          </Tooltip>
          {agent.companion && (
            <span className="text-[11px] text-fg-subtle">companion</span>
          )}
        </span>
        <span className="mt-0.5 block text-[12px] leading-[17px] text-fg-muted">
          {agent.reads} → {agent.produces}
        </span>
      </span>
      {agent.route && (
        <span
          role="link"
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onOpen(agent) }}
          className="mt-0.5 hidden shrink-0 items-center gap-1 text-[11px] font-medium text-fg-subtle transition-colors duration-150 group-hover:text-brand sm:inline-flex"
        >
          Open <ArrowRight size={11} />
        </span>
      )}
    </button>
  )
}

function Detail({ agent, onClose, onOpen, canOpen }) {
  const Icon = agentIcon(agent.icon)
  const kind = kindMeta(agent.kind)
  return (
    <div className="sticky top-4 rounded-lg border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2.5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-brand-subtle text-brand">
            <Icon size={16} />
          </span>
          <div className="min-w-0">
            <h2 className="text-h3 text-fg">{agent.name}</h2>
            <p className="text-caption text-fg-subtle">{kind.label}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="-mr-1 -mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-fg-subtle transition-colors duration-150 hover:bg-surface-3 hover:text-fg focus:outline-none focus-visible:shadow-ring"
        >
          <X size={15} />
        </button>
      </div>

      <p className="mt-3 text-[13px] leading-6 text-fg-muted">{agent.description}</p>

      <dl className="mt-4 space-y-3 border-t border-line pt-4 text-[13px]">
        <div>
          <dt className="text-caption text-fg-subtle">Reads</dt>
          <dd className="mt-0.5 text-fg-muted">{agent.reads}</dd>
        </div>
        <div>
          <dt className="text-caption text-fg-subtle">Produces</dt>
          <dd className="mt-0.5 text-fg-muted">{agent.produces}</dd>
        </div>
        <div>
          {/* Deliberately the last and most prominent line: every one of these
              proposes, and the auditor owns the conclusion. */}
          <dt className="text-caption text-brand">You decide</dt>
          <dd className="mt-0.5 font-medium text-fg">{agent.you_decide}</dd>
        </div>
      </dl>

      <p className="mt-4 border-t border-line pt-3 text-[11px] text-fg-subtle">
        {TIER_NOTE[agent.tier] || TIER_NOTE.draft}
      </p>

      {agent.route && (
        <button
          type="button"
          onClick={() => onOpen(agent)}
          disabled={!canOpen}
          className="mt-4 inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-md bg-brand px-3 text-sm font-medium text-brand-fg transition-opacity duration-150 hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:shadow-ring"
        >
          {canOpen ? <>Open {agent.name} <ArrowRight size={14} /></> : 'Choose an audit to open this'}
        </button>
      )}
    </div>
  )
}

export default function AgentsPage() {
  const navigate = useNavigate()
  const activeEngagement = useStore((s) => s.activeEngagement)
  const [kindFilter, setKindFilter] = useState('all')
  const [selected, setSelected] = useState(null)

  const { data } = useQuery({
    queryKey: ['agent-catalog'],
    queryFn: getAgentCatalog,
    staleTime: Infinity,
  })
  const { data: spend } = useQuery({
    queryKey: ['agent-spend', activeEngagement?.id],
    queryFn: () => getAgentSpend(activeEngagement.id),
    enabled: !!activeEngagement?.id,
  })

  const agents = data?.agents || []
  const counts = useMemo(() => {
    const out = { all: agents.length }
    for (const a of agents) out[a.kind] = (out[a.kind] || 0) + 1
    return out
  }, [agents])

  const shown = kindFilter === 'all' ? agents : agents.filter((a) => a.kind === kindFilter)

  const open = (agent) => {
    if (!activeEngagement?.id || !agent.route) return
    const base = agent.base ? `${agent.base}/` : ''
    navigate(`/engagements/${activeEngagement.id}/${base}${agent.route}`)
  }

  return (
    <PageContainer>
      <PageHeader
        title="Agents"
        subtitle={
          activeEngagement
            ? `${agents.length} agents across the audit lifecycle · open on ${activeEngagement.name}`
            : `${agents.length} agents across the audit lifecycle`
        }
      />

      <Toolbar
        trailing={spend?.spend?.calls > 0 && (
          <span className="text-[11px] text-fg-subtle">
            {spend.spend.calls} call{spend.spend.calls === 1 ? '' : 's'} on this audit
            {spend.spend.total_usd > 0 && ` · $${spend.spend.total_usd.toFixed(2)}`}
            {/* A reply that had to be cut into shape before it would parse is a
                call that nearly failed. Counted apart from the failures and from
                the clean runs, because it is neither. */}
            {spend.spend.repaired > 0 && ` · ${spend.spend.repaired} needed fixing`}
            {spend.spend.failed > 0 && ` · ${spend.spend.failed} failed`}
          </span>
        )}
      >
        <Segmented
          value={kindFilter}
          onChange={setKindFilter}
          options={[
            { value: 'all', label: `All ${counts.all}`, hint: 'Every step of an audit, whoever does the work.' },
            ...['agent', 'engine', 'your step'].map((k) => ({
              value: k, label: `${kindMeta(k).label} ${counts[k] || 0}`, icon: kindMeta(k).icon, hint: kindMeta(k).hint,
            })),
          ]}
        />
      </Toolbar>

      <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          {PHASES.map((phase) => {
            const rows = shown.filter((a) => a.phase === phase.key)
            if (!rows.length) return null
            return (
              <Section
                key={phase.key}
                title={phase.label}
                divided={false}
                action={<span className="text-caption text-fg-subtle">{rows.length}</span>}
              >
                <div className="mt-2 rounded-lg border border-line bg-surface">
                  {rows.map((a) => (
                    <Row
                      key={a.key}
                      agent={a}
                      active={selected?.key === a.key}
                      onSelect={setSelected}
                      onOpen={open}
                    />
                  ))}
                </div>
              </Section>
            )
          })}
        </div>

        <div>
          {selected ? (
            <Detail
              agent={selected}
              onClose={() => setSelected(null)}
              onOpen={open}
              canOpen={!!activeEngagement?.id}
            />
          ) : (
            <div className="rounded-lg border border-line bg-surface-2 p-4 text-[13px] leading-6 text-fg-muted">
              <p>
                Every agent here <span className="font-medium text-fg">proposes</span>. None of them
                decides anything: each one states what it reads, what it hands back, and what stays
                with you.
              </p>
              <p className="mt-3 text-fg-subtle">Select one to see its detail.</p>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
