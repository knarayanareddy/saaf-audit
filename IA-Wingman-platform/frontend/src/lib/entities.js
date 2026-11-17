// Single source of truth for entity + audit-type metadata (frontend mirror of
// the backend OrganizationProfile). White-label: generic business units, no
// organisation-specific naming. Branding/org name comes from GET /api/org.
//
// Colour policy: colour means something, or it isn't there. Entities and audit
// types carry NO colour of their own — in a bar list the length already carries
// the value, and fourteen competing hues only made the dashboard noisy. Status
// is the one categorical dimension that keeps colour, as a single ordered ramp
// through the audit lifecycle (see --chart-* in index.css). Risk severity has
// its own three tokens (--sev-*). Nothing else gets a hue.
import { tokenColor } from './color'

export const ENTITY_ORDER = ['GRP', 'RET', 'BUS', 'AM', 'INT']

export const ENTITIES = {
  GRP: { label: 'Group', short: 'GRP' },
  RET: { label: 'Retail', short: 'RET' },
  BUS: { label: 'Business', short: 'BUS' },
  AM: { label: 'Asset Management', short: 'AM' },
  INT: { label: 'International', short: 'INT' },
}

export const entityLabel = (e) => ENTITIES[e]?.label || e

export const AUDIT_TYPES = {
  compliance: { label: 'Compliance' },
  it: { label: 'IT' },
  operational: { label: 'Operational' },
  financial: { label: 'Financial' },
  esg: { label: 'ESG' },
  fraud: { label: 'Fraud' },
  conduct: { label: 'Conduct' },
  advisory: { label: 'Advisory' },
  validation: { label: 'Validation' },
}
export const auditTypeLabel = (t) => AUDIT_TYPES[t]?.label || t

// A soft tone per phase, walking the lifecycle from a neutral grey through sand,
// blue and lilac to green. Pastel on purpose: five of these sit next to each
// other in a donut, and saturated hues there is what made the old dashboard
// restless. `ink` is the same hue at text strength.
export const STATUS_META = {
  to_be_scheduled: { label: 'To be scheduled', token: '--status-scheduled' },
  in_planning: { label: 'In Planning', token: '--status-planning' },
  in_fieldwork: { label: 'In Fieldwork', token: '--status-fieldwork' },
  in_reporting: { label: 'In Reporting', token: '--status-reporting' },
  closed: { label: 'Closed', token: '--status-closed' },
}
export const statusLabel = (s) => STATUS_META[s]?.label || s
export const statusToken = (s) => STATUS_META[s]?.token || '--status-scheduled'
// alpha is optional: statusColor('closed', 0.16) gives the matching tint.
export const statusColor = (s, alpha) => tokenColor(statusToken(s), alpha)
// Text laid ON that tint — a pastel is a fill, never a label.
export const statusInk = (s, alpha) => tokenColor(`${statusToken(s)}-ink`, alpha)

export const ACTIVE_STATUSES = new Set(['in_planning', 'in_fieldwork', 'in_reporting'])
