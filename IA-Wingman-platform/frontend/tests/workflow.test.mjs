// Tests for the Workflow page layout model. No framework/deps — runs with:
//   node --test tests/workflow.test.mjs   (from the frontend/ directory)
// The fixture is the backend's method_map() output. backend/tests/test_workflow.py
// fails when it drifts, so this suite always runs against the real lifecycle graph.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  GRID, POSITIONS, buildLayout, chainOf, waitingOn, tourFor, beatEdges,
  narrationOf, durationFor, panGroups, MIN_BEAT_MS, MAX_BEAT_MS,
} from '../src/lib/workflowLayout.js'

const method = JSON.parse(readFileSync(new URL('./fixtures/workflow-method.json', import.meta.url), 'utf8'))
const layout = buildLayout(method)

// Beats that deliberately highlight no stage: they explain the platform itself.
const FRAMING = new Set(['lifecycle', 'assistant'])

const overlaps = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h

test('every node is placed on the map and no two cards overlap', () => {
  assert.equal(layout.nodes.length, method.nodes.length)
  for (let i = 0; i < layout.nodes.length; i++) {
    for (let j = i + 1; j < layout.nodes.length; j++) {
      assert.ok(!overlaps(layout.nodes[i], layout.nodes[j]), `${layout.nodes[i].key} overlaps ${layout.nodes[j].key}`)
    }
  }
})

test('every lifecycle node has a hand-tuned position inside the grid', () => {
  for (const n of method.nodes) assert.ok(POSITIONS[n.key], `no position for ${n.key}`)
  for (const n of layout.nodes) {
    assert.ok(n.x >= GRID.padX && n.x + n.w <= layout.width - GRID.padX, `${n.key} is outside the grid`)
  }
})

test('lines entering a band land on its top row', () => {
  for (const e of layout.edges) {
    const a = layout.byKey[e.from]
    const b = layout.byKey[e.to]
    if (a.band !== b.band) assert.equal(b.row, 0, `${e.from} -> ${e.to} lands on row ${b.row}`)
  }
})

test('lines between bands run in gutters and gaps, clear of every card', () => {
  const across = layout.edges.filter((e) => e.gutterX !== undefined)
  assert.ok(across.length > 0)
  for (const e of across) {
    for (const n of layout.nodes) {
      assert.ok(!(e.gutterX > n.x && e.gutterX < n.x + n.w), `${e.id} gutter runs through ${n.key}`)
      assert.ok(!(e.runY > n.y && e.runY < n.y + n.h), `${e.id} crossing runs through ${n.key}`)
    }
  }
})

test('every edge has a drawable path that ends on the edge of its target', () => {
  for (const e of layout.edges) {
    assert.match(e.path, /^M -?[\d.]+ -?[\d.]+ /)
    const b = layout.byKey[e.to]
    const onEdge = e.end.y === b.y || e.end.y === b.y + b.h || e.end.x === b.x || e.end.x === b.x + b.w
    assert.ok(onEdge, `${e.id} does not end on ${e.to}`)
  }
})

test('tracing a stage lights up what it waits on and what it unlocks', () => {
  const chain = chainOf('work_program', layout.edges)
  for (const k of ['scope', 'frameworks', 'topic_intelligence', 'drl', 'fieldwork', 'findings', 'report_draft']) {
    assert.ok(chain.has(k), `work_program chain misses ${k}`)
  }
  assert.ok(!chain.has('quality_review'), 'cross-cutting checks are not part of the gate chain')
  assert.ok(chainOf('supervisory_guidance', layout.edges).has('frameworks'), 'a companion traces to the stage it assists')
})

test('a locked stage explains what it is waiting on', () => {
  const signedOffPending = { ...layout.byKey, work_program: { ...layout.byKey.work_program, status: 'complete' } }
  assert.deepEqual(waitingOn({ ...layout.byKey.fieldwork, status: 'locked' }, signedOffPending), ['Work Program sign-off'])

  const programOpen = { ...layout.byKey, work_program: { ...layout.byKey.work_program, status: 'available' } }
  assert.deepEqual(waitingOn({ ...layout.byKey.drl, status: 'locked' }, programOpen), ['Work Program'])
  assert.deepEqual(waitingOn({ ...layout.byKey.drl, status: 'available' }, programOpen), [])
})

test('a stage the map does not know yet still gets a free cell', () => {
  const extended = {
    ...method,
    nodes: [...method.nodes, { key: 'future_step', label: 'Future step', phase: 'reporting', gates: ['report_draft'], kind: 'sequential' }],
    edges: [...method.edges, { from: 'report_draft', to: 'future_step', kind: 'gate' }],
  }
  const l = buildLayout(extended)
  const added = l.byKey.future_step
  assert.ok(added, 'future_step was dropped')
  for (const other of l.nodes) {
    if (other.key !== added.key) assert.ok(!overlaps(added, other), `future_step overlaps ${other.key}`)
  }
})

test('the tour only points at real stages, and a live audit ends on its next gate', () => {
  const beats = tourFor(method)
  assert.ok(beats.length >= 7)
  for (const b of beats) {
    assert.ok(b.title && b.text && b.duration > 0, `${b.id} is incomplete`)
    for (const k of b.focus) assert.ok(layout.byKey[k], `${b.id} points at unknown ${k}`)
    // A beat either points at stages on the map or is one of the two framing
    // beats, which talk about the platform rather than a step. Naming them keeps
    // "this beat highlights nothing" from becoming an easy thing to add.
    if (!FRAMING.has(b.id)) assert.ok(b.focus.length > 0, `${b.id} highlights nothing`)
  }
  const unlock = beats.find((b) => b.id === 'unlock')
  assert.ok(beatEdges(unlock, layout.edges).some((e) => e.from === 'work_program' && e.to === 'fieldwork'))

  const live = tourFor({ ...method, engagement: { id: 'e1' }, next_gate: 'racm_governance', summary: '14/22 lifecycle stages complete.' })
  assert.equal(live.at(-1).id, 'now')
  assert.deepEqual(live.at(-1).focus, ['racm_governance'])
})

test('every beat carries a spoken line, and it matches what is on screen', () => {
  for (const b of tourFor(method)) {
    assert.ok(b.narration?.length > 20, `${b.id} has nothing to say`)
    assert.ok(b.narration.includes(b.text), `${b.id} says something other than its caption`)
    assert.ok(!b.narration.includes('..'), `${b.id} would be read with a stumble`)
  }
})

test('a beat lasts as long as its sentence needs, within sane bounds', () => {
  const short = durationFor('Short.')
  const long = durationFor('x'.repeat(400))
  assert.equal(short, MIN_BEAT_MS, 'a short line still gets room to land')
  assert.equal(long, MAX_BEAT_MS, 'a long line cannot stall the tour')
  assert.ok(durationFor('x'.repeat(120)) > durationFor('x'.repeat(60)), 'longer text, longer beat')

  for (const b of tourFor(method)) {
    assert.ok(b.duration >= MIN_BEAT_MS && b.duration <= MAX_BEAT_MS, `${b.id}: ${b.duration}ms`)
    assert.equal(b.duration, durationFor(b.narration), `${b.id} is not timed by its own narration`)
  }
})

test('the tour explains the agents an auditor would otherwise never meet', () => {
  // Each of these was on the map but never narrated, so a viewer left the demo
  // without knowing the platform had it. The pairs say which beat owns which
  // subject, so moving a subject is a deliberate edit rather than a silent loss.
  const beats = tourFor(method)
  const text = beats.map((b) => `${b.title}. ${b.text}`).join(' ')
  const focusOf = (id) => new Set(beats.find((b) => b.id === id)?.focus || [])

  for (const key of ['process_understanding', 'supervisory_guidance', 'kickoff', 'anl',
    'interview_guide', 'interview_companion', 'vendor_guard', 'privacy_guard']) {
    assert.ok(beats.some((b) => b.focus.includes(key)), `no beat points at ${key}`)
  }

  assert.ok(/Process Understanding/.test(text), 'Process Understanding is never named')
  assert.ok(/Supervisory Guidance/.test(text), 'Supervisory Guidance is never named')
  assert.ok(/Vendor Guard/.test(text) && /Privacy Guard/.test(text), 'the guards are never named')
  assert.ok(/Interview Guide/.test(text), 'the interview guide is never named')

  // The two facts a viewer most often gets wrong about the method.
  assert.ok(/part one/i.test(text) && focusOf('kickoff').has('kickoff'),
    'the kick-off is not placed in part one of planning')
  assert.ok(/Audit Notification Letter/.test(text) && focusOf('anl').has('scope'),
    'the notification letter is not tied to Scope & Objectives')

  // The assistant is how an auditor reaches every one of these agents; a tour
  // that skips it leaves people looking for a button that does not exist.
  const assistant = beats.find((b) => b.id === 'assistant')
  assert.ok(assistant && /assistant/i.test(assistant.text), 'the assistant is not explained')

  // The document request list used to be matched to the tests by comparing
  // words. A tour that still describes it as "keeping the gaps in sight" would
  // be selling the older, vaguer thing.
  const evidence = beats.find((b) => b.id === 'evidence')
  assert.ok(/what evidence it needs/i.test(evidence.text),
    'the tour does not say that a test declares what it needs')
  assert.ok(/settle|covers/i.test(evidence.text),
    'nor that a request names the tests it settles')

  const quality = beats.find((b) => b.id === 'quality')
  assert.ok(/by reference/i.test(quality.text) && /guess/i.test(quality.text),
    'the coverage beat does not distinguish a reference from a guess')
})

test('the narrated tour runs long enough to sit through, and not a second longer', () => {
  // Measured with the voice muted, where `duration` is what actually governs.
  // The scripted tour was 113s and was asked to grow by 30-60 seconds; the upper
  // bound is the real constraint, because past three minutes nobody watches.
  const total = tourFor(method).reduce((s, b) => s + b.duration, 0) / 1000
  assert.ok(total >= 143 && total <= 173, `scripted tour runs ${total.toFixed(1)}s`)
})

test('no beat is written past the point where its clock stops growing', () => {
  // durationFor clamps at MAX_BEAT_MS. A beat written past that ceiling reads on
  // screen for less time than it needs, so the caption is pulled away mid-
  // sentence whenever the voice is muted.
  for (const b of tourFor(method)) {
    if (b.id === 'now') continue // live text from the backend, length not ours
    assert.ok(b.duration < MAX_BEAT_MS, `${b.id} is too long to be read in full`)
  }
})

test('every stage a beat points at actually reaches the screen', () => {
  // The bug this locks down: "chasing the evidence" named Isabelle and then
  // scrolled to the Document Request List, three bands above her, so she was
  // narrated and never shown. Beats reaching across bands are taller than any
  // window, which is why WorkflowPage pans — focus[0] first, the rest partway
  // through. Here that pan is replayed against the real geometry.
  //
  // 500px is a deliberately mean viewport: a 900px window at 150% browser zoom
  // leaves about 600 CSS pixels, and the caption bar takes roughly 104 of them.
  const USABLE = 500
  const box = (keys) => {
    const ns = keys.map((k) => layout.byKey[k]).filter(Boolean)
    const top = Math.min(...ns.map((n) => n.y))
    return { top, height: Math.max(...ns.map((n) => n.y + n.h)) - top }
  }
  // Where the window lands after WorkflowPage centres a group — or gives up and
  // shows its top card with a little headroom.
  // `panGroups` is the same function WorkflowPage drives the scrolling with, so
  // deleting the pan there breaks this test rather than quietly passing it.
  const windowFor = (keys) => {
    const { top, height } = box(keys)
    return top - (height <= USABLE ? (USABLE - height) / 2 : 24)
  }
  const seenIn = (winTop, key) => {
    const n = layout.byKey[key]
    return n.y >= winTop && n.y + n.h <= winTop + USABLE
  }

  for (const beat of tourFor(method)) {
    const keys = beat.focus.filter((k) => layout.byKey[k])
    if (!keys.length) continue

    const stages = panGroups(keys, (g) => box(g).height, USABLE).map(windowFor)

    for (const key of keys) {
      assert.ok(stages.some((winTop) => seenIn(winTop, key)),
        `${beat.id}: ${key} is narrated but never scrolled into view`)
    }
  }
})

test('the live closing beat is timed by its own summary, not a fixed number', () => {
  const short = tourFor({ ...method, engagement: { id: 'e1' }, summary: 'Nearly done.' }).at(-1)
  const wordy = tourFor({ ...method, engagement: { id: 'e1' }, summary: 'x'.repeat(200) }).at(-1)
  assert.ok(wordy.duration > short.duration)
})

test('a title that already ends in a full stop does not gain a second one', () => {
  assert.equal(narrationOf({ title: 'AI proposes. You decide.', text: 'Quality runs throughout.' }),
    'AI proposes. You decide. Quality runs throughout.')
})
