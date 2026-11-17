// A correction to an audit's details that the assistant proposes (propose_update_engagement_details).
//
// The card shows it and the accept button applies it, so both read it the same way: only
// the five fields the tool offers, trimmed, and only those that actually change. The
// server checks the rest (a name can never be saved empty).

export const DETAIL_FIELDS = {
  name: 'Name',
  audit_code: 'Audit code',
  summary: 'Summary',
  lead_auditor: 'Lead auditor',
  scope_period: 'Scope period',
}

/** The fields to send to PATCH /engagements/{id}. `current` is what the audit has now, when known. */
export function detailPayload(input, current = {}) {
  const payload = {}
  for (const key of Object.keys(DETAIL_FIELDS)) {
    const value = typeof input?.[key] === 'string' ? input[key].trim() : ''
    if (!value) continue // never blank a field through a proposal
    if (value === (current?.[key] ?? '')) continue // nothing would change
    payload[key] = value
  }
  return payload
}

/** One line per change for the action card: "Name: Old → New" where the old value is known. */
export function detailLines(input, current = {}) {
  return Object.entries(detailPayload(input, current)).map(([key, value]) => {
    const before = current?.[key]
    return `${DETAIL_FIELDS[key]}: ${before ? `${before} → ` : ''}${value}`
  })
}
