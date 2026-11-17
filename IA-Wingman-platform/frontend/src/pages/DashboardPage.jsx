import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Sparkles } from 'lucide-react'
import { getEngagements, getEngagementStats } from '../api/engagements'
import { useStore } from '../store/useStore'
import { useOrg } from '../lib/useOrg'
import {
  ENTITY_ORDER, AUDIT_TYPES,
  entityLabel, auditTypeLabel, statusLabel, statusColor, statusToken, ACTIVE_STATUSES,
} from '../lib/entities'
import Section from '../components/ui/Section'
import MetricStrip from '../components/ui/MetricStrip'
import { StatusBadge } from '../components/ui/Badge'
import { SkeletonCard } from '../components/ui/Skeleton'
import DonutChart from '../components/charts/DonutChart'
import BarList from '../components/charts/BarList'
import TimelineChart from '../components/charts/TimelineChart'
import Button from '../components/ui/Button'
import DailyBriefing from '../components/dashboard/DailyBriefing'

export default function DashboardPage() {
  const navigate = useNavigate()
  const org = useOrg()
  const currentUser = useStore((s) => s.currentUser)
  const toggleChat = useStore((s) => s.toggleChat)
  const setCreateEngagementOpen = useStore((s) => s.setCreateEngagementOpen)

  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: getEngagementStats })
  const { data: engagements = [], isPending } = useQuery({ queryKey: ['engagements'], queryFn: getEngagements })

  const count = (pred) => engagements.filter(pred).length

  const statusSegments = ['in_planning', 'in_fieldwork', 'in_reporting', 'to_be_scheduled', 'closed']
    .map((s) => ({ key: s, label: statusLabel(s), value: count((e) => e.status === s), color: statusColor(s) }))
    .filter((s) => s.value > 0)

  const entityBars = ENTITY_ORDER
    .map((e) => ({ key: e, label: entityLabel(e), value: count((x) => x.entity === e) }))
    .filter((b) => b.value > 0)

  const typeBars = Object.keys(AUDIT_TYPES)
    .map((t) => ({ key: t, label: auditTypeLabel(t), value: count((x) => x.audit_type === t) }))
    .filter((b) => b.value > 0)
    .sort((a, b) => b.value - a.value)

  const timelineRows = engagements
    .filter((e) => ACTIVE_STATUSES.has(e.status) && e.start_date)
    .sort((a, b) => (a.start_date || '').localeCompare(b.start_date || ''))
    .slice(0, 12)

  const goStatus = (s) => navigate(`/engagements?status=${s}`)

  const metrics = [
    { key: 'active', value: stats?.active ?? '—', label: 'Active', hint: 'Planning, fieldwork or reporting', accent: statusToken('in_fieldwork'), onClick: () => goStatus('active') },
    { key: 'planning', value: stats?.in_planning ?? '—', label: 'In planning', accent: statusToken('in_planning'), onClick: () => goStatus('in_planning') },
    { key: 'fieldwork', value: stats?.in_fieldwork ?? '—', label: 'In fieldwork', accent: statusToken('in_fieldwork'), onClick: () => goStatus('in_fieldwork') },
    { key: 'reporting', value: stats?.in_reporting ?? '—', label: 'In reporting', accent: statusToken('in_reporting'), onClick: () => goStatus('in_reporting') },
  ]

  return (
    <div className="mx-auto max-w-7xl px-6 py-6">
      {/* Masthead: who and what, then straight into the work. */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p className="text-meta">
          {org.name} · Internal Audit portfolio · {stats?.total ?? engagements.length} engagements
        </p>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={toggleChat}><Sparkles size={14} /> AI Assistant</Button>
          <Button size="sm" onClick={() => setCreateEngagementOpen(true)}><Plus size={14} /> New engagement</Button>
        </div>
      </div>

      {/* 1 — what needs attention now (deterministic) */}
      <DailyBriefing engagements={engagements} isPending={isPending} currentUser={currentUser} />

      {/* 2 — where the portfolio stands: four numbers, one strip */}
      <MetricStrip className="mt-6" items={metrics} />

      {/* 3 — how it is distributed. Three columns, one frame, hairlines between. */}
      <div className="mt-6 rounded-lg border border-line bg-surface">
        {isPending ? (
          <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-3">
            <SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
        ) : (
          <div className="grid grid-cols-1 divide-y divide-line-subtle lg:grid-cols-3 lg:divide-x lg:divide-y-0">
            <div className="min-w-0 p-4">
              <h2 className="text-caption mb-3">By status</h2>
              <DonutChart
                segments={statusSegments}
                size={132}
                thickness={14}
                centerValue={stats?.total ?? engagements.length}
                centerLabel="audits"
                onSegmentClick={goStatus}
              />
            </div>
            <div className="min-w-0 p-4">
              <h2 className="text-caption mb-3">By entity</h2>
              <BarList items={entityBars} onItemClick={(e) => navigate(`/engagements?entity=${e}`)} />
            </div>
            <div className="min-w-0 p-4">
              <h2 className="text-caption mb-3">By audit type</h2>
              <BarList items={typeBars} onItemClick={(t) => navigate(`/engagements?type=${t}`)} />
            </div>
          </div>
        )}
      </div>

      {/* 4 — active work per entity, as plain rows */}
      <Section className="mt-6" title="Active by entity" divided={false}>
        <div className="grid grid-cols-1 gap-x-8 pt-2 sm:grid-cols-2 lg:grid-cols-3">
          {ENTITY_ORDER.map((entity) => {
            const items = engagements.filter((e) => e.entity === entity && ACTIVE_STATUSES.has(e.status)).slice(0, 3)
            if (items.length === 0) return null
            return (
              <div key={entity} className="py-1">
                <div className="text-caption py-1">{entityLabel(entity)}</div>
                <div className="divide-y divide-line-subtle">
                  {items.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => navigate(`/engagements/${e.id}/planning`)}
                      className="flex w-full items-center justify-between gap-2 py-1.5 text-left text-[13px] transition-colors duration-150 hover:bg-surface-2"
                    >
                      <span className="min-w-0 truncate text-fg">{e.name}</span>
                      <StatusBadge status={e.status} />
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </Section>

      {/* 5 — what is coming */}
      <Section
        className="mt-6"
        title="Planning timeline"
        divided={false}
        action={
          <button onClick={() => navigate('/engagements')} className="text-xs text-fg-muted transition-colors duration-150 hover:text-fg">
            View all →
          </button>
        }
      >
        <div className="pt-3">
          <TimelineChart rows={timelineRows} onRowClick={(r) => navigate(`/engagements/${r.id}/planning`)} />
        </div>
      </Section>
    </div>
  )
}
