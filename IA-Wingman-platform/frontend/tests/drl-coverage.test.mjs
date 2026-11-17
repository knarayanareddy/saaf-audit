// The DRL's coverage strip reads the keys the endpoint actually sends.
//
// Run from the frontend dir:  node --test tests/drl-coverage.test.mjs
//
// The endpoint spread its counts and its detail rows into one object, so every
// list silently overwrote its own count and the page crashed rendering an array
// where a number belonged ("Objects are not valid as a React child"). Counts
// now live at the top level and rows under `detail`, and these tests hold the
// two sides of that contract together across the language boundary.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const page = readFileSync(
  fileURLToPath(new URL('../src/pages/planning/DRLPage.jsx', import.meta.url)), 'utf8')
const service = readFileSync(
  fileURLToPath(new URL('../../backend/services/evidence_needs.py', import.meta.url)), 'utf8')
const router = readFileSync(
  fileURLToPath(new URL('../../backend/routers/phase3.py', import.meta.url)), 'utf8')

/** The endpoint's body, read from the router itself. */
function endpointBody() {
  const block = router.match(/async def drl_coverage[\s\S]*?\n\n\n/)
  assert.ok(block, 'the endpoint is where the test expects it')
  return block[0]
}

/** Every top-level field the endpoint sends: summary()'s counts plus its own. */
function topLevelKeys() {
  const summary = service.match(/def summary\(self\) -> dict:\s*return \{([\s\S]*?)\n        \}/)
  assert.ok(summary, 'summary() is where the test expects it')
  const keys = new Set([...summary[1].matchAll(/"([a-z_]+)":/g)].map((m) => m[1]))
  // The endpoint adds fields of its own, at one level of indentation inside
  // the returned dict — anything deeper belongs to `detail`.
  for (const m of endpointBody().matchAll(/\n        "([a-z_]+)":/g)) keys.add(m[1])
  keys.delete('detail')
  return keys
}

/** Every `coverage.<key>` the page reads. */
function keysUsedByPage() {
  return new Set([...page.matchAll(/\bcoverage\.([a-z_]+)/g)].map((m) => m[1]))
}

test('every field the page reads is a field the endpoint sends', () => {
  const sent = topLevelKeys()
  for (const key of keysUsedByPage()) {
    if (key === 'detail') continue
    assert.ok(sent.has(key), `coverage.${key} is not sent by the endpoint`)
  }
})

test('the detail rows are read from detail, never from the count', () => {
  // `coverage.unrequested` is a number; the rows behind it are
  // `coverage.detail.unrequested`. Reading the first as a list is the crash.
  assert.ok(page.includes('coverage.detail?.unrequested'),
    'the page reads the rows from detail')
  assert.ok(!/coverage\.unrequested[?.]*\.(map|slice|join|length)/.test(page),
    'and never treats the count as a list')
})

test('the endpoint keeps them apart', () => {
  const body = endpointBody()
  assert.ok(body.includes('"detail": {'), 'rows are nested under detail')
  assert.ok(body.includes('**cov.summary()'), 'and the counts are spread at the top level')
})

test('the advice matches what the auditor can actually do', () => {
  // A signed work program cannot be regenerated, so telling its auditor to
  // regenerate it is the one instruction they cannot follow.
  assert.ok(topLevelKeys().has('work_program_signed'),
    'the endpoint says whether regenerating is still possible')
  assert.ok(page.includes('coverage.work_program_signed'), 'and the page asks')
  assert.ok(page.includes('cannot be regenerated'), 'and says so instead')
})

test('a request that settles nothing is visible on its own row', () => {
  // The strip gives the total; an auditor deciding whether to drop one request
  // needs it on the row. `covers` is what the generator recorded while merging.
  assert.ok(page.includes('item.covers'), 'the row reads what the request covers')
  assert.ok(page.includes('no test'), 'and says so when it covers nothing')
})

test('the strip explains an empty result instead of showing four zeros', () => {
  assert.ok(page.includes('coverage.needs === 0'),
    'the page distinguishes "nothing declared yet" from "everything is covered"')
})

test('generating refreshes the figures it just changed', () => {
  // Generating rewrites which needs each request settles. Without this the
  // strip showed the previous run's numbers until someone reloaded — the one
  // number the screen exists for, stale at the moment it moves.
  const block = page.match(/const invalidateAll = \(\) => \{[\s\S]*?\n  \}/)
  assert.ok(block, 'invalidateAll is where the test expects it')
  assert.ok(block[0].includes("'drl-coverage'"), 'the cover figures are invalidated too')
  assert.ok(page.includes('invalidateAll()'), 'and generating calls it')
})
