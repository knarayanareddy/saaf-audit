// A scope item can be traced back to the step that produced it.
//
// Run from the frontend dir:  node --test tests/scope-sources.test.mjs
//
// The screen used to tag a row "AI" when its source was the string 'cascaded',
// and show nothing otherwise — so the fourteen items that did record an
// accurate origin displayed none. The label now travels with the row from the
// backend; the only thing this side decides is which page to open, so that map
// is what these tests guard.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { STEP_ROUTES, originOf, originPath } from '../src/lib/scopeSources.js'

const SRC = fileURLToPath(new URL('../src/', import.meta.url))
const app = readFileSync(SRC + 'App.jsx', 'utf8')
const page = readFileSync(SRC + 'pages/planning/ScopeObjectivesPage.jsx', 'utf8')

/** The producers the backend can name (generated from services/scope_sources.py). */
const sources = JSON.parse(
  readFileSync(new URL('./fixtures/scope-sources.json', import.meta.url), 'utf8'),
)

test('every producing step has a page to open', () => {
  for (const { key, step, label } of sources) {
    if (!step) {
      // `manual`: a person typed it, so there is nothing upstream to open.
      assert.equal(STEP_ROUTES[step], undefined, `${key} needs no route`)
      assert.ok(label, `${key} still needs a label`)
      continue
    }
    const route = STEP_ROUTES[step]
    assert.ok(route, `${key} -> ${step} has no route`)
    assert.ok(
      app.includes(`/engagements/:id/planning/${route}`),
      `/engagements/:id/planning/${route} is a real route`,
    )
  }
})

test('the map holds no route that is not a producer', () => {
  const steps = new Set(sources.map((s) => s.step).filter(Boolean))
  for (const step of Object.keys(STEP_ROUTES)) {
    assert.ok(steps.has(step), `${step} is a producer the backend knows`)
  }
})

test('originOf carries what the backend sent', () => {
  const row = {
    source: 'from_bra',
    source_label: 'Background Risk Assessment',
    source_step: 'bra',
    source_ref: 'run-7',
  }
  const origin = originOf(row)
  assert.equal(origin.label, 'Background Risk Assessment')
  assert.equal(origin.ref, 'run-7')
  assert.equal(originPath('e1', row), '/engagements/e1/planning/bra')
})

test('a manual item has a label but nowhere to go', () => {
  const row = { source: 'manual', source_label: 'Entered by the auditor', source_step: '' }
  assert.equal(originOf(row).label, 'Entered by the auditor')
  assert.equal(originPath('e1', row), '', 'no link, because nothing upstream produced it')
})

test('an item with no origin renders nothing rather than a guess', () => {
  assert.equal(originOf({}).label, '')
  assert.equal(originOf(undefined).label, '')
  assert.equal(originPath('e1', {}), '')
})

test('the screen no longer decides the label itself', () => {
  // The old rule, verbatim, is what this is here to stop coming back.
  assert.ok(!page.includes("'cascaded'"), 'no page compares against the old ambiguous string')
  assert.ok(page.includes('originOf('), 'the origin comes from one place')
  const label = sources.find((s) => s.step === 'frameworks').label
  assert.ok(!page.includes(label), `the page does not restate "${label}"`)
})
