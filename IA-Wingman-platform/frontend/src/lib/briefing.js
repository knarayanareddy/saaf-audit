// Daily Briefing — deterministic selection of "what needs my attention now".
//
// PURE + DETERMINISTIC by design: no AI decides what is important or how to rank
// it. Every item is derived from data the app already has (engagement fields +
// the board narrative's stale flag). Same input → same output, always. This file
// has no React/DOM imports so it can be unit-tested with `node --test`.
//
// Sorting rule (fixed, documented):
//   rank 0  overdue            — a dated milestone is in the past
//   rank 1  missing ownership  — an active audit has no lead / no fieldwork dates
//   rank 2  upcoming deadline  — a report milestone falls within DEADLINE_WINDOW_DAYS
//   rank 3  ready for review   — the copilot has auto-drafted work waiting on the auditor
//   rank 4  other              — portfolio-level attention (stale board report)
// Ties within a rank break on a rule-specific secondary key, then engagement
// name, then id — so ordering is always stable.

export const ACTIVE_STATUSES = new Set(['in_planning', 'in_fieldwork', 'in_reporting'])
export const DEADLINE_WINDOW_DAYS = 14

const RANK = { overdue: 0, ownership: 1, deadline: 2, review: 3, other: 4 }

function toDay(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return null
  const d = new Date(`${dateStr}T00:00:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

// Whole-day difference (target - now); negative = in the past.
function daysBetween(dateStr, now) {
  const target = toDay(dateStr)
  if (!target) return null
  const base = new Date(`${now.toISOString().slice(0, 10)}T00:00:00`)
  return Math.round((target - base) / 86_400_000)
}

// Build the flat list of attention items from existing data only.
// `engagements`: array from GET /api/engagements. `board`: GET /api/board/narrative
// (may be null/undefined — the stale rule is simply skipped then). `reviewCounts`:
// GET /api/copilot/ready-for-review-counts, {engagement_id: count} (may be
// null/undefined — the review rule is simply skipped then, same pattern as board).
export function buildBriefing(engagements = [], board = null, now = new Date(), reviewCounts = null) {
  const items = []

  for (const e of Array.isArray(engagements) ? engagements : []) {
    const active = ACTIVE_STATUSES.has(e.status)

    // rank 3 — the copilot auto-drafted something and it's waiting on the auditor.
    const readyCount = reviewCounts?.[e.id] || 0
    if (active && readyCount > 0) {
      items.push({
        key: `review:${e.id}`,
        rank: RANK.review,
        // Higher counts sort first within this rank (ascending on sortKey, so
        // invert the count) — more waiting work reads as more urgent.
        sortKey: String(9999 - readyCount).padStart(4, '0'),
        title: `${readyCount} step${readyCount === 1 ? '' : 's'} ready for review`,
        engagement: e.name,
        reason: 'The copilot auto-drafted these and is waiting on you to accept or dismiss.',
        action: 'Open Agent Studio',
        href: `/engagements/${e.id}/agents`,
        meta: `${readyCount} waiting`,
        tone: 'review',
      })
    }

    // rank 0 — planning overdue (a scheduled planning date has passed, still not started)
    if (e.status === 'to_be_scheduled') {
      const d = daysBetween(e.planning_date, now)
      if (d !== null && d < 0) {
        items.push({
          key: `overdue:${e.id}`,
          rank: RANK.overdue,
          sortKey: e.planning_date,
          title: 'Planning overdue',
          engagement: e.name,
          reason: `Planning was due ${Math.abs(d)} day${Math.abs(d) === 1 ? '' : 's'} ago and has not started.`,
          action: 'Open planning',
          href: `/engagements/${e.id}/planning`,
          meta: `${Math.abs(d)}d overdue`,
          tone: 'overdue',
        })
      }
    }

    // rank 1 — missing ownership. One item per engagement: lead takes precedence.
    if (active && !e.lead_auditor) {
      items.push({
        key: `nolead:${e.id}`,
        rank: RANK.ownership,
        sortKey: e.name || '',
        title: 'No lead assigned',
        engagement: e.name,
        reason: 'An active audit has no lead auditor assigned.',
        action: 'Assign a lead',
        href: `/engagements/${e.id}/planning`,
        meta: null,
        tone: 'ownership',
      })
    } else if (active && !e.start_date) {
      items.push({
        key: `nodates:${e.id}`,
        rank: RANK.ownership,
        sortKey: e.name || '',
        title: 'No fieldwork dates',
        engagement: e.name,
        reason: 'An active audit has no fieldwork start date set.',
        action: 'Set fieldwork dates',
        href: `/engagements/${e.id}/planning`,
        meta: null,
        tone: 'ownership',
      })
    }

    // rank 2 — upcoming report deadline (soonest of draft/final within the window, not past)
    if (active) {
      const candidates = [
        ['Draft report', e.draft_report_date],
        ['Final report', e.final_report_date],
      ]
        .map(([label, date]) => ({ label, date, d: daysBetween(date, now) }))
        .filter((c) => c.d !== null && c.d >= 0 && c.d <= DEADLINE_WINDOW_DAYS)
        .sort((a, b) => a.d - b.d)
      if (candidates.length > 0) {
        const c = candidates[0]
        items.push({
          key: `deadline:${e.id}`,
          rank: RANK.deadline,
          sortKey: c.date,
          title: `${c.label} due soon`,
          engagement: e.name,
          reason: `${c.label} is due in ${c.d} day${c.d === 1 ? '' : 's'}.`,
          action: 'Open reporting',
          href: `/engagements/${e.id}/reporting`,
          meta: c.d === 0 ? 'due today' : `${c.d}d left`,
          tone: 'deadline',
        })
      }
    }
  }

  // rank 3 — portfolio: the AI board narrative lags the current figures.
  if (board && board.generated_by === 'ai' && board.stale === true) {
    items.push({
      key: 'board:stale',
      rank: RANK.other,
      sortKey: '',
      title: 'Board report is out of date',
      engagement: 'Portfolio',
      reason: 'The board narrative was drafted before the portfolio changed — figures may lag.',
      action: 'Open board report',
      href: '/board',
      meta: null,
      tone: 'other',
    })
  }

  items.sort(
    (a, b) =>
      a.rank - b.rank ||
      String(a.sortKey).localeCompare(String(b.sortKey)) ||
      String(a.engagement).localeCompare(String(b.engagement)) ||
      a.key.localeCompare(b.key),
  )
  return items
}

// Split into the primary (shown) items and the remaining count.
export function splitBriefing(items, max = 3) {
  const primary = items.slice(0, max)
  return { primary, remaining: Math.max(0, items.length - primary.length) }
}
