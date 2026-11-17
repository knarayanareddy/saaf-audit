import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle, UserPlus, Clock, FileWarning, ChevronRight, ArrowRight, Inbox,
} from 'lucide-react'
import { getBoardNarrative } from '../../api/board'
import { getReadyForReviewCounts } from '../../api/ai'
import { buildBriefing, splitBriefing } from '../../lib/briefing'

// The Daily Briefing answers "what needs my attention now?" before any portfolio
// statistics. Selection + ordering are 100% deterministic (see lib/briefing.js) —
// no AI decides importance. Every item links straight to the object to act on.
//
// Presentation is exception-driven: one 36px line per item, severity carried by a
// 2px marker and an icon rather than by a tinted tile. An attention list should
// read like a log, not like a set of adverts.

const TONE = {
  overdue: { Icon: AlertTriangle, mark: 'bg-sev-high', icon: 'text-sev-high' },
  ownership: { Icon: UserPlus, mark: 'bg-sev-med', icon: 'text-sev-med' },
  deadline: { Icon: Clock, mark: 'bg-chart-3', icon: 'text-fg-muted' },
  review: { Icon: Inbox, mark: 'bg-brand', icon: 'text-brand' },
  other: { Icon: FileWarning, mark: 'bg-line-strong', icon: 'text-fg-subtle' },
}

function greetingFor(now = new Date()) {
  const h = now.getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

function BriefingItem({ item }) {
  const navigate = useNavigate()
  const tone = TONE[item.tone] || TONE.other
  const { Icon } = tone
  return (
    <button
      onClick={() => navigate(item.href)}
      className="group flex w-full items-center gap-2.5 py-2 pl-2 pr-1 text-left transition-colors duration-150 hover:bg-surface-2"
      title={item.reason}
    >
      <span className={`h-5 w-0.5 shrink-0 rounded-full ${tone.mark}`} />
      <Icon size={14} className={`shrink-0 ${tone.icon}`} />
      <span className="min-w-0 flex-1 truncate text-[13px] text-fg">
        <span className="font-medium">{item.title}</span>
        <span className="text-fg-subtle"> · {item.engagement}</span>
      </span>
      <span className="hidden min-w-0 max-w-[40%] shrink truncate text-meta lg:block">{item.reason}</span>
      {item.meta && <span className="shrink-0 text-meta tabular-nums">{item.meta}</span>}
      <ArrowRight size={13} className="shrink-0 text-fg-subtle opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
    </button>
  )
}

export default function DailyBriefing({ engagements = [], isPending = false, currentUser }) {
  const [showAll, setShowAll] = useState(false)
  // Board narrative feeds the single portfolio-level rule (stale report). Optional:
  // if it fails, the briefing simply omits that one rule and still renders.
  const { data: board } = useQuery({
    queryKey: ['board-narrative'],
    queryFn: getBoardNarrative,
    staleTime: 60_000,
  })
  const { data: reviewCounts } = useQuery({
    queryKey: ['copilot-review-counts'],
    queryFn: getReadyForReviewCounts,
    staleTime: 30_000,
  })

  const greeting = greetingFor()
  const items = buildBriefing(engagements, board, new Date(), reviewCounts)
  const { primary, remaining } = splitBriefing(items, 4)
  const shown = showAll ? items : primary

  return (
    <section>
      <div className="flex h-7 items-end justify-between gap-3 border-b border-line">
        <h1 className="text-h2 text-fg">
          {greeting}{currentUser ? `, ${currentUser}` : ''}
        </h1>
        <span className="text-meta">
          {isPending
            ? 'Building your briefing…'
            : items.length === 0
              ? 'Nothing needs your attention'
              : `${items.length} item${items.length === 1 ? '' : 's'} need attention`}
        </span>
      </div>

      {isPending ? (
        <div className="space-y-px pt-2" aria-busy="true">
          {[0, 1, 2].map((i) => <div key={i} className="h-9 animate-pulse rounded bg-surface-3" />)}
        </div>
      ) : items.length === 0 ? (
        <p className="py-3 text-[13px] text-fg-muted">
          Everything is on track — no overdue items, missing leads or looming deadlines.
        </p>
      ) : (
        <ul className="motion-safe:animate-fade-in-up divide-y divide-line-subtle">
          {shown.map((item) => (
            <li key={item.key}><BriefingItem item={item} /></li>
          ))}
        </ul>
      )}

      {!isPending && remaining > 0 && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="mt-1.5 flex items-center gap-1 pl-2 text-xs text-fg-muted transition-colors duration-150 hover:text-fg"
        >
          <ChevronRight size={13} className={`transition-transform duration-150 ${showAll ? 'rotate-90' : ''}`} />
          {showAll ? 'Show fewer' : `Show all ${items.length}`}
        </button>
      )}
    </section>
  )
}
