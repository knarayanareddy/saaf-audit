// Tests for the deterministic Daily Briefing logic. No framework/deps — runs with:
//   node --test tests/briefing.test.mjs   (from the frontend/ directory)
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildBriefing, splitBriefing } from '../src/lib/briefing.js'

// Fixed "now" so date-relative rules are reproducible.
const NOW = new Date('2026-07-21T09:00:00Z')
const iso = (offsetDays) => {
  const d = new Date('2026-07-21T00:00:00Z')
  d.setUTCDate(d.getUTCDate() + offsetDays)
  return d.toISOString().slice(0, 10)
}

const eng = (over) => ({
  id: 'e1', name: 'Alpha Audit', entity: 'GRP', audit_type: 'compliance',
  status: 'in_planning', lead_auditor: 'Lead Auditor', start_date: iso(5),
  planning_date: null, draft_report_date: null, final_report_date: null, ...over,
})

test('no-lead rule fires only for active engagements without a lead', () => {
  const items = buildBriefing([eng({ lead_auditor: null })], null, NOW)
  assert.equal(items.length, 1)
  assert.equal(items[0].title, 'No lead assigned')
  assert.equal(items[0].href, '/engagements/e1/planning')
})

test('a fully-staffed active engagement produces no items', () => {
  assert.equal(buildBriefing([eng()], null, NOW).length, 0)
})

test('no-lead takes precedence over no-dates (one ownership item per engagement)', () => {
  const items = buildBriefing([eng({ lead_auditor: null, start_date: null })], null, NOW)
  assert.equal(items.length, 1)
  assert.equal(items[0].title, 'No lead assigned')
})

test('planning overdue fires for a past planning date on a to_be_scheduled audit', () => {
  const items = buildBriefing(
    [eng({ status: 'to_be_scheduled', planning_date: iso(-3), lead_auditor: 'X', start_date: null })],
    null, NOW,
  )
  assert.equal(items.length, 1)
  assert.equal(items[0].title, 'Planning overdue')
  assert.equal(items[0].meta, '3d overdue')
})

test('deadline rule fires within the window but not when past or beyond it', () => {
  assert.equal(buildBriefing([eng({ draft_report_date: iso(5) })], null, NOW)[0].title, 'Draft report due soon')
  assert.equal(buildBriefing([eng({ draft_report_date: iso(30) })], null, NOW).length, 0) // beyond window
  assert.equal(buildBriefing([eng({ draft_report_date: iso(-1) })], null, NOW).length, 0) // past
})

test('stale board item only when narrative is AI-generated AND stale', () => {
  assert.equal(buildBriefing([], { generated_by: 'ai', stale: true }, NOW).length, 1)
  assert.equal(buildBriefing([], { generated_by: 'ai', stale: false }, NOW).length, 0)
  assert.equal(buildBriefing([], { generated_by: 'deterministic', stale: true }, NOW).length, 0)
  assert.equal(buildBriefing([], null, NOW).length, 0)
})

test('items are ordered by rank: overdue → ownership → deadline → review → other', () => {
  const items = buildBriefing(
    [
      eng({ id: 'a', name: 'A', draft_report_date: iso(3) }),                                   // deadline
      eng({ id: 'b', name: 'B', lead_auditor: null }),                                          // ownership
      eng({ id: 'c', name: 'C', status: 'to_be_scheduled', planning_date: iso(-2), start_date: null }), // overdue
      eng({ id: 'd', name: 'D' }),                                                              // review
    ],
    { generated_by: 'ai', stale: true }, NOW, { d: 2 },
  )
  assert.deepEqual(items.map((i) => i.tone), ['overdue', 'ownership', 'deadline', 'review', 'other'])
})

test('review rule fires only for active engagements with a positive ready count', () => {
  assert.equal(buildBriefing([eng()], null, NOW, { e1: 3 })[0].title, '3 steps ready for review')
  assert.equal(buildBriefing([eng()], null, NOW, { e1: 1 })[0].title, '1 step ready for review')
  assert.equal(buildBriefing([eng()], null, NOW, { e1: 0 }).length, 0)
  assert.equal(buildBriefing([eng()], null, NOW, null).length, 0)
  assert.equal(buildBriefing([eng({ status: 'closed' })], null, NOW, { e1: 3 }).length, 0)
})

test('ties within a rank are resolved deterministically (soonest deadline first)', () => {
  const items = buildBriefing(
    [
      eng({ id: 'a', name: 'A', draft_report_date: iso(9) }),
      eng({ id: 'b', name: 'B', draft_report_date: iso(2) }),
    ],
    null, NOW,
  )
  assert.deepEqual(items.map((i) => i.engagement), ['B', 'A'])
})

test('splitBriefing caps primary at max and reports the remainder', () => {
  const many = Array.from({ length: 5 }, (_, i) => eng({ id: `x${i}`, name: `E${i}`, lead_auditor: null }))
  const { primary, remaining } = splitBriefing(buildBriefing(many, null, NOW), 3)
  assert.equal(primary.length, 3)
  assert.equal(remaining, 2)
})

test('empty and malformed input never throws', () => {
  assert.equal(buildBriefing([], null, NOW).length, 0)
  assert.equal(buildBriefing(undefined, undefined, NOW).length, 0)
  // missing name / null dates must not crash
  assert.doesNotThrow(() => buildBriefing([{ id: 'z', status: 'in_planning', lead_auditor: null }], null, NOW))
})
