// The action card names a stage the way every other surface names it.
//
// Run from the frontend dir:  node --test tests/action-card.test.mjs
//
// This file held its own STAGE_LABELS map, marked "cosmetic only — keep in sync
// with orchestrator.py". It was not kept in sync: it knew 15 of the 26 stages,
// so a card proposing scope, fieldwork, findings or any companion asked the
// auditor to accept 'racm_evidence_chase'. The registry exists to end exactly
// that, and these tests keep the map from growing back.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src/', import.meta.url))
const REGISTRY = fileURLToPath(new URL('../../backend/services/agent_registry.py', import.meta.url))

const card = readFileSync(SRC + 'components/ai/ActionCard.jsx', 'utf8')
const activityLog = readFileSync(SRC + 'components/ai/ActivityLog.jsx', 'utf8')
const registry = readFileSync(REGISTRY, 'utf8')

// Comments explain the decisions; they are not code. The comment left where the
// map used to be names the keys it failed to cover — stripping comments stops a
// rule failing on the sentence that documents it.
const code = card.replace(/\/\/.*/g, '').replace(/\/\*[\s\S]*?\*\//g, '')

/** Every agent key the backend registry declares a presentation for. */
function registryKeys() {
  const block = registry.match(/_PRESENTATION: dict\[str, dict\] = \{([\s\S]*?)\n\}/)
  assert.ok(block, 'the presentation table is where the test expects it')
  return [...block[1].matchAll(/^ {4}"([a-z_]+)": dict\(/gm)].map((m) => m[1])
}

test('the local stage-label map is gone', () => {
  assert.ok(!/STAGE_LABELS/.test(code), 'no STAGE_LABELS map or lookup remains')
  assert.ok(!/keep in sync with/i.test(card),
    'nothing here claims to be kept in sync by hand any more')
})

test('no stage key is spelled out in the component at all', () => {
  const keys = registryKeys()
  assert.ok(keys.length >= 26, `expected the full roster, got ${keys.length}`)

  // A label map is only one shape the duplication can take. Any stage key
  // written here — in an object, an array, a switch — is the same mistake, so
  // the rule is the key itself rather than the map it sat in.
  //
  // Prose is not a key. STATUS_LABELS legitimately reads 'In fieldwork', and a
  // status is not an agent: it has no registry row to read a name from. So the
  // bare-identifier check runs with string literals removed, and quoted keys
  // are caught separately, in key position.
  const bare = new Set(code.replace(/'[^']*'|"[^"]*"|`[^`]*`/g, ' ').split(/[^A-Za-z0-9_]+/))
  const quotedKey = (k) => new RegExp(`['"]${k}['"]\\s*:`).test(code)

  const present = keys.filter((k) => bare.has(k) || quotedKey(k))
  assert.deepEqual(present, [], 'these stage keys belong to the registry, not to this file')
})

test('the stage name comes from the registry', () => {
  assert.match(code, /import \{ agentName, indexAgents \} from '\.\.\/\.\.\/lib\/agents'/,
    'ActionCard reads the registry helpers')
  assert.match(code, /agentName\(input\.stage_key, agents\)/,
    'the run-stage card resolves its key through agentName')
  assert.match(code, /indexAgents\(catalog\?\.agents\)/,
    'the catalog is indexed, so aliases resolve too')
})

test('it reads the catalog the same way the activity log does', () => {
  for (const source of [code, activityLog]) {
    assert.match(source, /queryKey: \['agent-catalog'\]/, 'one cache key for the roster')
    assert.match(source, /staleTime: Infinity/, 'fetched once a session, not per card')
  }
  assert.match(code, /getAgentCatalog/, 'through the shared api client')
})

test('a stage key never reaches the screen raw', () => {
  // agentName's own fallback covers a key the registry has not caught up with;
  // the card must not route around it with `|| input.stage_key`.
  assert.ok(!/\|\|\s*input\.stage_key/.test(code),
    'no raw-key fallback beside the registry lookup')
})
