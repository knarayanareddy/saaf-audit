import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, Network } from 'lucide-react'
import { getEngagement } from '../api/engagements'
import { useStore } from '../store/useStore'
import { EntityBadge, StatusBadge } from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { Card, SectionHeading } from '../components/ui/Card'
import PhaseTabs from '../components/engagement/PhaseTabs'
import CoverageMatrix from '../components/review/CoverageMatrix'
import ReviewPanel from '../components/review/ReviewPanel'
import AiSharePanel from '../components/review/AiSharePanel'

// The Quality phase gathers everything about quality, coverage and consistency:
// the Risk & Control Matrix (the traceable spine), the deterministic coverage &
// consistency sweep, and the AI Peer Reviewer. Agents that check the other agents.
export default function QualityHubPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const toggleChat = useStore((s) => s.toggleChat)

  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })

  useEffect(() => {
    if (eng) setActiveEngagement(eng)
  }, [eng, setActiveEngagement])

  if (!eng) return <div className="px-8 py-8 text-sm text-fg-subtle">Loading…</div>

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
            Quality, coverage &amp; consistency — the agents that check the other agents.
          </p>
        </div>
        <Button variant="secondary" onClick={toggleChat}><Sparkles size={16} /> AI</Button>
      </div>

      <PhaseTabs engagementId={id} active="quality" />

      <button
        onClick={() => navigate(`/engagements/${id}/racm`)}
        className="mt-6 flex w-full items-start gap-4 rounded-lg border border-brand/20 bg-brand-faint p-5 text-left transition hover:border-brand/40"
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand text-brand-fg">
          <Network size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-fg">Risk &amp; Control Matrix</div>
          <p className="mt-0.5 text-sm text-fg-muted">
            The traceable spine: objective → risk → control → test → evidence. Every agent writes here, so each result stays traceable — AI proposes, you own.
          </p>
        </div>
        <span className="shrink-0 text-sm font-medium text-brand">Open →</span>
      </button>

      <div className="mt-8">
        <SectionHeading>AI share in this file</SectionHeading>
        <p className="mt-1 text-sm text-fg-muted">
          What IA Wingman proposed and what people did with it — counted from the records themselves, and from the edit register for changes since it started.
        </p>
        <Card className="mt-4 p-5">
          <AiSharePanel engagementId={id} />
        </Card>
      </div>

      <div className="mt-8">
        <SectionHeading>Coverage, consistency &amp; peer review</SectionHeading>
        <p className="mt-1 text-sm text-fg-muted">
          The consistency sweep runs instantly; the Peer Reviewer is AI-assisted and opt-in — every comment is a proposal you accept or dismiss.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-5">
            <CoverageMatrix engagementId={id} />
          </Card>
          <Card className="p-5">
            <ReviewPanel engagementId={id} />
          </Card>
        </div>
      </div>
    </div>
  )
}
