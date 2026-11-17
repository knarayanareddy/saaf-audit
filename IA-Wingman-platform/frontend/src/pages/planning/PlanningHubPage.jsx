import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, Hexagon, Target, FileText, Users, BarChart2, ShieldCheck, ClipboardList, FileSearch, MessagesSquare, Workflow, BookOpen } from 'lucide-react'
import { getEngagement } from '../../api/engagements'
import { useStore } from '../../store/useStore'
import { EntityBadge, StatusBadge } from '../../components/ui/Badge'
import ProgressRing from '../../components/ui/ProgressRing'
import Button from '../../components/ui/Button'
import { Card, SectionHeading } from '../../components/ui/Card'
import ActivityLog from '../../components/ai/ActivityLog'
import PhaseTabs from '../../components/engagement/PhaseTabs'
import JurisdictionSelect from '../../components/planning/JurisdictionSelect'

const MODULES = [
  { key: 'topic_intelligence', route: 'topic-intelligence', icon: Sparkles, title: 'Topic Intelligence' },
  { key: 'kickoff', route: 'kickoff', icon: Users, title: 'Kick-off' },
  { key: 'process_understanding', route: 'process-understanding', icon: Hexagon, title: 'Process Understanding' },
  { key: 'framework_requirements', route: 'framework-requirements', icon: ShieldCheck, title: 'Laws & Regulations' },
  { key: 'supervisory_guidance', route: 'supervisory-guidance', icon: BookOpen, title: 'Supervisory Guidance' },
  { key: 'scope_objectives', route: 'scope-objectives', icon: Target, title: 'Scope & Objectives' },
  { key: 'anl', route: 'anl', icon: FileText, title: 'Audit Notification Letter' },
  { key: 'bra', route: 'bra', icon: BarChart2, title: 'Background Risk Assessment' },
  { key: 'resource_plan', route: 'resource-plan', icon: Users, title: 'Resource Planning' },
  { key: 'work_program', route: 'work-program', icon: ClipboardList, title: 'Work Program' },
  { key: 'drl', route: 'drl', icon: FileSearch, title: 'Document Request List' },
]

export default function PlanningHubPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const toggleChat = useStore((s) => s.toggleChat)

  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })

  useEffect(() => {
    if (eng) setActiveEngagement(eng)
  }, [eng, setActiveEngagement])

  if (!eng) return <div className="px-8 py-8 text-sm text-fg-subtle">Loading…</div>
  const progress = eng.planning_progress || {}
  const labels = progress.labels || {}
  const overall = Math.round(
    MODULES.reduce((s, m) => s + (progress[m.key] ?? 0), 0) / MODULES.length,
  )
  const nextStep = MODULES.find((m) => (progress[m.key] ?? 0) < 100)

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
      <div className="flex items-start justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <EntityBadge entity={eng.entity} />
            <StatusBadge status={eng.status} />
          </div>
          <h1 className="text-h1 text-fg">{eng.name}</h1>
          <p className="mt-1 text-sm text-fg-muted">
            {eng.audit_code ? `Audit code: ${eng.audit_code}` : 'No audit code'}
            {eng.scope_period ? ` · Scope: ${eng.scope_period}` : ''}
          </p>
        </div>
        <Button variant="secondary" onClick={toggleChat}><Sparkles size={16} /> AI</Button>
      </div>

      <PhaseTabs engagementId={id} active="planning" />

      <Card className="mt-6 p-5">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="text-caption text-fg-subtle">Planning progress</div>
            {nextStep ? (
              <div className="mt-1 truncate text-sm text-fg">
                Next recommended step: <span className="font-medium text-brand">{nextStep.title}</span>
              </div>
            ) : (
              <div className="mt-1 text-sm font-medium text-sev-low">All planning modules complete</div>
            )}
          </div>
          <div className="text-2xl font-semibold tabular-nums text-brand">{overall}%</div>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-3">
          <div className="h-full rounded-full bg-brand transition-[width] duration-500" style={{ width: `${overall}%` }} />
        </div>
        <div className="mt-4 border-t border-line pt-3">
          <JurisdictionSelect engagementId={id} />
        </div>
      </Card>

      <div className="stagger mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {MODULES.map(({ key, route, icon: Icon, title }) => {
          const pct = progress[key] ?? 0
          const label = labels[key] || (pct === 0 ? 'Not started' : pct === 100 ? 'Complete' : 'In progress')
          return (
            <button
              key={key}
              onClick={() => navigate(`/engagements/${id}/planning/${route}`)}
              className="border border-line flex flex-col rounded-xl bg-surface p-5 text-left transition hover:"
            >
              <div className="flex items-start justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-subtle text-brand">
                  <Icon size={18} />
                </div>
                <ProgressRing value={pct} />
              </div>
              <h3 className="mt-3 font-medium text-fg">{title}</h3>
              <p className="mt-1 text-sm text-fg-muted">{label}</p>
              <span className="mt-3 text-sm font-medium text-brand">Open →</span>
            </button>
          )
        })}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[
          {
            route: 'planning/interview', icon: MessagesSquare, title: 'Interview studio',
            desc: 'Persona guide with traceability + a live companion that turns answers into follow-ups, observations and minutes.',
          },
          {
            route: 'agents', icon: Workflow, title: 'Agent Studio',
            desc: 'See the orchestration: a gated planning cascade and a live run-graph of the AI agents at work.',
          },
        ].map(({ route, icon: Icon, title, desc }) => (
          <button
            key={route}
            onClick={() => navigate(`/engagements/${id}/${route}`)}
            className="flex items-start gap-4 rounded-lg border border-brand/20 bg-brand-faint p-5 text-left transition hover:border-brand/40"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-fg">
              <Icon size={20} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-sm font-semibold text-fg">
                {title} <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[11px] font-semibold text-brand">AI</span>
              </div>
              <p className="mt-0.5 text-sm text-fg-muted">{desc}</p>
            </div>
          </button>
        ))}
      </div>

      <Card className="mt-8 p-5">
        <SectionHeading>AI activity & provenance</SectionHeading>
        <ActivityLog engagementId={id} />
      </Card>
    </div>
  )
}
