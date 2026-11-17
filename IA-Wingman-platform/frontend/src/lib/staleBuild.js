// After a deploy, a tab still running the previous build asks for page chunks
// whose hashed names no longer exist. The import fails and the page shows the
// error panel — the first thing a demo audience saw after the 2026-10-23
// deploys. Reloading fetches the new index.html, which names the new chunks.

const KEY = 'ia_reloaded_for_new_version'

// The messages browsers give for a dynamic import that could not be loaded:
// Chrome, Firefox and Safari word it differently, and a server answering with a
// page of HTML instead of a script shows up as a MIME-type error.
const STALE = /dynamically imported module|Importing a module script failed|error loading dynamically imported|Loading chunk|Expected a JavaScript module|MIME type/i

export function isStaleBuildError(error) {
  return STALE.test(String(error?.message || error || ''))
}

/**
 * Reload once to pick up the new build. Returns false — and does nothing — when
 * a reload already happened in the last 30 seconds: then the error is not a
 * stale tab, and looping would hide it.
 */
export function reloadForNewVersion(storage = globalThis.sessionStorage, now = Date.now(), reload = () => globalThis.location.reload()) {
  try {
    const last = Number(storage.getItem(KEY) || 0)
    if (now - last < 30_000) return false
    storage.setItem(KEY, String(now))
  } catch {
    return false
  }
  reload()
  return true
}
