import client, { downloadFile } from './client'

// The whole spine (flat, parent-linked lists) for one engagement.
export const getSpine = (id) =>
  client.get(`/racm/${id}`).then((r) => r.data)

// Spine nodes — nodeType is one of: objectives | risks | controls | tests | evidence
export const createNode = (id, nodeType, payload) =>
  client.post(`/racm/${id}/${nodeType}`, payload).then((r) => r.data)
export const updateNode = (id, nodeType, nodeId, payload) =>
  client.patch(`/racm/${id}/${nodeType}/${nodeId}`, payload).then((r) => r.data)
export const deleteNode = (id, nodeType, nodeId) =>
  client.delete(`/racm/${id}/${nodeType}/${nodeId}`).then((r) => r.data)

// Accept an AI-proposed node (the "you own" flip). Who accepted is not sent:
// the backend takes it from the actor header, so the record cannot say "You".
export const acceptNode = (id, nodeType, nodeId) =>
  updateNode(id, nodeType, nodeId, { accepted: true })

// Planning & Scoping engine (deterministic; front-loads the spine from planning)
export const getScopingPreview = (id) =>
  client.get(`/racm/${id}/agents/scoping/preview`).then((r) => r.data)
export const runScoping = (id) =>
  client.post(`/racm/${id}/agents/scoping/run`).then((r) => r.data)

// Governance-Document Assessor (opt-in AI; writes gap proposals into the spine)
export const getGovernanceAssessment = (id) =>
  client.get(`/racm/${id}/agents/governance-assessment`).then((r) => r.data)
export const runGovernanceAssessment = (id) =>
  client.post(`/racm/${id}/agents/governance-assessment/run`).then((r) => r.data)

// Close the loop: promote a test's exceptions to a traceable 5C finding
export const promoteTestToFinding = (id, testId) =>
  client.post(`/racm/${id}/tests/${testId}/promote-to-finding`).then((r) => r.data)

// Control-Testing / Sampling agent (deterministic; proposes a test under a control)
export const proposeControlTest = (id, controlId) =>
  client.post(`/racm/${id}/controls/${controlId}/propose-test`).then((r) => r.data)

// Evidence / DRL chaser (deterministic; matches DRL to evidence)
export const getEvidenceChase = (id) =>
  client.get(`/racm/${id}/agents/evidence-chase`).then((r) => r.data)

// Data-Analysis / Anomaly agent (deterministic run is free; narrate = opt-in AI)
export const getDataAnalysis = (id) =>
  client.get(`/racm/${id}/agents/data-analysis`).then((r) => r.data)
export const runDataAnalysis = (id, narrate = false) =>
  client.post(`/racm/${id}/agents/data-analysis/run`, null, { params: { narrate } }).then((r) => r.data)

// Privacy Guard (deterministic GDPR data-minimisation; free, no AI, no spine writes)
export const getPrivacyGuard = (id) =>
  client.get(`/racm/${id}/agents/privacy-guard`).then((r) => r.data)
export const runPrivacyGuard = (id, { role = 'auditor', purpose = 'customer_due_diligence', justification } = {}) =>
  client.post(`/racm/${id}/agents/privacy-guard/run`, null, {
    params: { role, purpose, justification: justification || undefined },
  }).then((r) => r.data)
export const downloadPrivacyAuditTrail = (id) =>
  downloadFile(`/racm/${id}/agents/privacy-guard/audit-trail`, 'privacy_audit_trail.jsonl')

// Vendor Guard (opt-in AI third-party risk assessment; deterministic scorecard + spine proposals)
export const getVendorGuard = (id) =>
  client.get(`/racm/${id}/agents/vendor-guard`).then((r) => r.data)
export const runVendorGuard = (id, payload) =>
  client.post(`/racm/${id}/agents/vendor-guard/run`, payload).then((r) => r.data)
export const downloadVendorGuardReport = (id) =>
  downloadFile(`/racm/${id}/agents/vendor-guard/export`, 'Vendor-Risk-Assessment.docx')

// Scope-decision log
export const createScopeDecision = (id, payload) =>
  client.post(`/racm/${id}/scope-decisions`, payload).then((r) => r.data)
export const updateScopeDecision = (id, sid, payload) =>
  client.patch(`/racm/${id}/scope-decisions/${sid}`, payload).then((r) => r.data)
export const deleteScopeDecision = (id, sid) =>
  client.delete(`/racm/${id}/scope-decisions/${sid}`).then((r) => r.data)
