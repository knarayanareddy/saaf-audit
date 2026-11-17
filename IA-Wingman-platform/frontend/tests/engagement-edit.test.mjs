// Correcting an audit's details from the assistant, and finding the edit from inside the audit.
//
// Run from the frontend dir:  node --test tests/engagement-edit.test.mjs
//
// Asked to fix a typo in an audit's name, the assistant said it had no tool for it and did
// not know where the name could be edited. The edit window existed, reachable only from the
// Engagements list. These keep the two ways in: the pencil beside the active audit, and the
// assistant's proposal, which shows what changes and never blanks a field.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { detailPayload, detailLines } from '../src/lib/engagementEdit.js'

const SRC = fileURLToPath(new URL('../src/', import.meta.url))
const read = (p) => readFileSync(SRC + p, 'utf8')

test('a proposal keeps only the five text fields, trimmed', () => {
  const input = {
    name: '  Artificial Intelligence ', audit_code: '26-047', status: 'closed', entity: 'RET',
    team_members: ['x'], rationale: 'typo',
  }
  assert.deepEqual(detailPayload(input), { name: 'Artificial Intelligence', audit_code: '26-047' })
})

test('a proposal never blanks a field, and drops what would not change', () => {
  assert.deepEqual(detailPayload({ name: '   ', summary: '' }), {}, 'blank values are ignored')
  assert.deepEqual(detailPayload({ name: 'Same', audit_code: '26-1' }, { name: 'Same', audit_code: '26-0' }),
    { audit_code: '26-1' }, 'an unchanged name is left out')
  assert.deepEqual(detailPayload(undefined), {})
})

test('the card shows old and new where the old value is known', () => {
  const lines = detailLines({ name: 'Artificial Intelligence', summary: 'New text' },
    { name: 'Artificial Intellegence' })
  assert.deepEqual(lines, ['Name: Artificial Intellegence → Artificial Intelligence', 'Summary: New text'])
  assert.deepEqual(detailLines({ name: 'Same' }, { name: 'Same' }), [], 'nothing would change: no lines')
})

test('the card and the accept button read a proposal the same way', () => {
  const card = read('components/ai/ActionCard.jsx')
  const panel = read('components/ai/AIChatPanel.jsx')
  assert.match(card, /propose_update_engagement_details/)
  assert.match(card, /detailLines\(/)
  assert.match(panel, /propose_update_engagement_details/)
  assert.match(panel, /detailPayload\(/)
  assert.match(panel, /setActiveEngagement\(updated\)/, 'the sidebar follows the saved result')
})

test('the edit pencil sits beside the active audit and opens the full edit window', () => {
  const sidebar = read('components/layout/LeftSidebar.jsx')
  assert.match(sidebar, /EditActiveEngagement/)
  assert.match(sidebar, /setEditOpen\(true\)/)
  const wrapper = read('components/engagement/EditActiveEngagement.jsx')
  assert.match(wrapper, /EditEngagementModal/)
  assert.match(wrapper, /getEngagement/, 'the full record is fetched; the store holds only a few fields')
  assert.match(wrapper, /createPortal/, 'the window is not trapped inside the narrow sidebar')
})
