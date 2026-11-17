import { Sparkles, Plus, Search, FileText } from 'lucide-react'
import { useState } from 'react'
import Button from '../../components/ui/Button'
import { Card, SectionHeading, Kbd } from '../../components/ui/Card'
import StatCard from '../../components/ui/StatCard'
import { EntityBadge, StatusBadge } from '../../components/ui/Badge'
import { ConfidenceBadge, SourceChip, SeverityTag } from '../../components/ui/Provenance'
import { Skeleton, SkeletonCard } from '../../components/ui/Skeleton'
import EmptyState from '../../components/ui/EmptyState'
import Collapsible from '../../components/ui/Collapsible'
import Tabs from '../../components/ui/Tabs'
import Segmented from '../../components/ui/Segmented'
import Tooltip from '../../components/ui/Tooltip'
import ThemeToggle from '../../components/theme/ThemeToggle'
import { ENTITY_ORDER } from '../../lib/entities'

const STATUSES = ['to_be_scheduled', 'in_planning', 'in_fieldwork', 'in_reporting', 'closed']

export default function ShowcasePage() {
  const [tab, setTab] = useState('a')
  const [seg, setSeg] = useState('list')
  return (
    <div className="mx-auto max-w-5xl px-8 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-fg">Primitives showcase</h1>
          <p className="mt-1 text-sm text-fg-muted">Design-system check — verify every primitive in light and dark.</p>
        </div>
        <ThemeToggle />
      </div>

      <section>
        <SectionHeading>Typography</SectionHeading>
        <Card className="space-y-2 p-6">
          <div className="text-display text-fg">Display 36</div>
          <div className="text-h1 text-fg">Heading 1 — 28</div>
          <div className="text-h2 text-fg">Heading 2 — 20</div>
          <div className="text-h3 text-fg">Heading 3 — 16</div>
          <div className="text-sm text-fg">Body — the quick brown fox jumps over the lazy dog.</div>
          <div className="text-sm text-fg-muted">Muted body text for secondary information.</div>
          <div className="text-caption text-fg-subtle">Caption label</div>
        </Card>
      </section>

      <section>
        <SectionHeading>Buttons</SectionHeading>
        <div className="flex flex-wrap items-center gap-3">
          <Button><Plus size={16} /> Primary</Button>
          <Button variant="secondary"><Sparkles size={16} /> Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="success">Success</Button>
          <Button size="sm">Small</Button>
          <Button disabled>Disabled</Button>
          <span className="text-sm text-fg-muted">Press <Kbd>⌘</Kbd> <Kbd>K</Kbd></span>
        </div>
      </section>

      <section>
        <SectionHeading>Stat cards</SectionHeading>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard value="10" label="Active audits" accent="--chart-1" icon={FileText} hint="+2 this quarter" />
          <StatCard value="4" label="In planning" accent="--chart-4" />
          <StatCard value="3" label="In fieldwork" accent="--chart-3" />
          <StatCard value="3" label="In reporting" accent="--chart-2" />
        </div>
      </section>

      <section>
        <SectionHeading>Badges & provenance</SectionHeading>
        <Card className="space-y-4 p-6">
          <div className="flex flex-wrap gap-2">{ENTITY_ORDER.map((e) => <EntityBadge key={e} entity={e} />)}</div>
          <div className="flex flex-wrap gap-2">{STATUSES.map((s) => <StatusBadge key={s} status={s} />)}</div>
          <div className="flex flex-wrap gap-2">
            <ConfidenceBadge level="high" /><ConfidenceBadge level="medium" /><ConfidenceBadge level="low" />
            <SourceChip type="document" /><SourceChip type="web" /><SourceChip type="model" />
            <SeverityTag level="must_fix" /><SeverityTag level="suggestion" /><SeverityTag level="info" />
          </div>
        </Card>
      </section>

      <section>
        <SectionHeading>Tabs & segmented</SectionHeading>
        <div className="space-y-4">
          <Tabs value={tab} onChange={setTab} tabs={[{ value: 'a', label: 'Planning', count: 10 }, { value: 'b', label: 'Fieldwork', count: 3 }, { value: 'c', label: 'Reporting' }]} />
          <Segmented value={seg} onChange={setSeg} options={[{ value: 'list', label: 'List', icon: Search }, { value: 'grid', label: 'Grid' }]} />
        </div>
      </section>

      <section>
        <SectionHeading>Collapsible (readable output)</SectionHeading>
        <div className="space-y-2">
          <Collapsible title="Key risk areas" count={3} defaultOpen badge={<ConfidenceBadge level="high" showLabel={false} />} icon={Sparkles}>
            <ul className="space-y-1.5 text-sm text-fg-muted">
              <li>• Customer due diligence completeness at onboarding.</li>
              <li>• Transaction monitoring alert handling and backlog.</li>
              <li>• Sanctions screening list coverage and tuning.</li>
            </ul>
          </Collapsible>
          <Collapsible title="Excluded from scope" count={1} icon={FileText}>
            <p className="text-sm text-fg-muted">Trade finance — covered by a separate 2026 engagement.</p>
          </Collapsible>
        </div>
      </section>

      <section>
        <SectionHeading>Loading & empty</SectionHeading>
        <div className="grid gap-4 sm:grid-cols-2">
          <SkeletonCard />
          <EmptyState icon={Search} title="Nothing to show yet" description="Run the analysis to populate this section." action={<Button size="sm">Run analysis</Button>} />
        </div>
        <div className="mt-3 flex gap-2"><Skeleton className="h-5 w-24" /><Skeleton className="h-5 w-16" /></div>
      </section>

      <section>
        <SectionHeading>Tooltip</SectionHeading>
        <Tooltip label="This is a tooltip"><Button variant="secondary">Hover me</Button></Tooltip>
      </section>
    </div>
  )
}
