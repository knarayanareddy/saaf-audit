// The frontend half of the agent registry.
//
// Run from the frontend dir:  node --test tests/agents.test.mjs
//
// The icon map is written by hand so the bundler can drop what is unused, which
// means a name the backend sends and the map does not hold would render as
// nothing at all. That is the failure this file exists to catch — in a test
// rather than in a demo.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src/', import.meta.url))
const REGISTRY = fileURLToPath(new URL('../../backend/services/agent_registry.py', import.meta.url))

const lib = readFileSync(SRC + 'lib/agents.js', 'utf8')
const registry = readFileSync(REGISTRY, 'utf8')

// Comments explain the decisions; they are not code. Stripping them before
// matching stops a rule failing on the sentence that documents it — agents.js
// says in prose why `lucide[name]` is avoided, which is not the same as doing it.
const code = lib.replace(/\/\/.*/g, '').replace(/\/\*[\s\S]*?\*\//g, '')

/** Every icon name the backend registry declares. */
function backendIcons() {
  return [...registry.matchAll(/icon="([A-Za-z0-9]+)"/g)].map((m) => m[1])
}

/** Every icon name the frontend map can resolve. */
function frontendIcons() {
  const block = lib.match(/const ICONS = \{([\s\S]*?)\n\}/)
  assert.ok(block, 'the ICONS map is where the test expects it')
  return block[1].split(',').map((s) => s.trim()).filter(Boolean)
}

test('the backend declares an icon for every agent', () => {
  const icons = backendIcons()
  assert.ok(icons.length >= 26, `expected the full roster, got ${icons.length}`)
  assert.equal(new Set(icons).size, icons.length, 'no two agents share an icon')
})

test('every icon the backend sends can be rendered', () => {
  const available = new Set(frontendIcons())
  const missing = backendIcons().filter((name) => !available.has(name))
  assert.deepEqual(missing, [], 'these icon names would render as nothing')
})

test('the icon map is explicit, so the bundler can drop what is unused', () => {
  assert.ok(!/lucide\[/.test(code), 'no dynamic lookup into the icon library')
  assert.match(code, /^import \{[\s\S]*?\} from 'lucide-react'/m,
    'icons are named imports')
})

test('an unknown icon falls back visibly rather than silently', () => {
  assert.match(lib, /return ICONS\[name\] \|\| Sparkles/,
    'agentIcon has a fallback')
})

test('the three kinds are the three the backend uses', () => {
  const backendKinds = [...registry.matchAll(/kind=(AGENT|ENGINE|HUMAN)/g)].map((m) => m[1])
  assert.ok(backendKinds.length >= 26, 'every agent declares a kind')
  const block = lib.match(/export const KINDS = \{([\s\S]*?)\n\}\n/)
  assert.ok(block, 'the KINDS map exists')
  for (const key of ['agent', 'engine', "'your step'"]) {
    assert.ok(block[1].includes(key.replace(/'/g, '')), `the frontend knows the kind ${key}`)
  }
})

test('a kind explains itself, because the word "agent" used to cover three things', () => {
  for (const phrase of ['AI proposes', 'Computed', 'Your step']) {
    assert.ok(lib.includes(phrase), `the label ${phrase} is present`)
  }
  assert.match(lib, /no model, no judgement, no cost/,
    'an engine says plainly that it costs nothing')
})

test('a name is never shown to a person as a raw key', () => {
  assert.match(lib, /replace\(\/_\/g, ' '\)/, 'agentName turns an unknown key into words')
  assert.ok(lib.includes("return 'Unknown agent'"), 'and a missing key says so')
})

test('aliases are indexed, so any name a layer used resolves to one row', () => {
  assert.match(lib, /for \(const alias of a\.aliases \|\| \[\]\) byKey\[alias\] = a/,
    'indexAgents walks the aliases')
})
