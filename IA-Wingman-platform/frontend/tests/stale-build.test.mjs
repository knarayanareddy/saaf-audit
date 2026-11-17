// A tab opened before a deploy asks for page chunks that no longer exist.
//
// Run from the frontend dir:  node --test tests/stale-build.test.mjs
//
// The app reloads once to pick up the new build, and only once: if the error is
// still there after a reload, it is not a stale tab and must be shown.
import test from 'node:test'
import assert from 'node:assert/strict'
import { isStaleBuildError, reloadForNewVersion } from '../src/lib/staleBuild.js'

test('the messages browsers give for a chunk that could not load are recognised', () => {
  for (const message of [
    'Failed to fetch dynamically imported module: https://x/assets/Page-abc.js', // Chrome
    'error loading dynamically imported module', // Firefox
    'Importing a module script failed.', // Safari
    "Failed to load module script: Expected a JavaScript module script but the server responded with a MIME type of \"text/html\"",
  ]) {
    assert.ok(isStaleBuildError(new Error(message)), message)
  }
})

test('an ordinary rendering bug is not mistaken for a stale tab', () => {
  assert.equal(isStaleBuildError(new TypeError("Cannot read properties of undefined (reading 'map')")), false)
  assert.equal(isStaleBuildError(null), false)
})

test('it reloads once, and not again within thirty seconds', () => {
  const store = new Map()
  const storage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) }
  let reloads = 0
  const reload = () => { reloads += 1 }
  assert.equal(reloadForNewVersion(storage, 1_000_000, reload), true)
  assert.equal(reloadForNewVersion(storage, 1_010_000, reload), false, 'a second failure right after is a real error')
  assert.equal(reloadForNewVersion(storage, 1_040_000, reload), true, 'a later deploy may reload again')
  assert.equal(reloads, 2)
})

test('without storage it does not reload at all, rather than loop', () => {
  const broken = { getItem: () => { throw new Error('blocked') }, setItem: () => {} }
  let reloads = 0
  assert.equal(reloadForNewVersion(broken, 1, () => { reloads += 1 }), false)
  assert.equal(reloads, 0)
})
