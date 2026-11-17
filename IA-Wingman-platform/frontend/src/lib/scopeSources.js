// Where a scope item came from, and where to go and look at it.
//
// The backend sends `source`, `source_label`, `source_step` and `source_ref`
// with every scope item and key audit question (services/scope_sources.py). The
// label travels with the row so this file never restates it — the one thing the
// browser knows that the backend does not is which page holds a step.
//
// `frameworks` is the registry's id; `framework-requirements` is the route. The
// planning hub calls the same module `framework_requirements`. Three names for
// one screen is one too many, and this map is where that shows.

export const STEP_ROUTES = {
  topic_intelligence: 'topic-intelligence',
  process_understanding: 'process-understanding',
  frameworks: 'framework-requirements',
  kickoff: 'kickoff',
  bra: 'bra',
}

// `manual` carries no step: an auditor typed it, and there is nothing to open.
export function originOf(row) {
  const step = row?.source_step || ''
  return {
    label: row?.source_label || '',
    step,
    route: STEP_ROUTES[step] || '',
    ref: row?.source_ref || '',
  }
}

export function originPath(engagementId, row) {
  const { route } = originOf(row)
  return route ? `/engagements/${engagementId}/planning/${route}` : ''
}
