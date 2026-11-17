import client, { downloadFile } from './client'

// Topic Intelligence
export const getTopicIntelligence = (id) =>
  client.get(`/planning/${id}/topic-intelligence`).then((r) => r.data)
// What the scan will be given, and what it will not — see services/scan_context.py
// The memo as a Word file, built on the server from the same answer the page reads.
export const exportTopicMemoWord = (id) =>
  downloadFile(`/planning/${id}/topic-intelligence/export-word`, 'Topic-Intelligence-memo.docx')
// Run one lens again; only that lens is replaced on the memo.
export const rerunTopicLens = (id, lens) =>
  client.post(`/planning/${id}/topic-intelligence/lens/${lens}/rerun`).then((r) => r.data)
export const getScanContext = (id) =>
  client.get(`/planning/${id}/topic-intelligence/context`).then((r) => r.data)
export const updateTopicIntelligence = (id, payload) =>
  client.patch(`/planning/${id}/topic-intelligence`, payload).then((r) => r.data)
export const updateLens4 = (id, payload) =>
  client.patch(`/planning/${id}/ti/lens4`, payload).then((r) => r.data)
export const acceptTopicIntelligence = (id) =>
  client.post(`/planning/${id}/topic-intelligence/accept`).then((r) => r.data)
export const discardTopicIntelligence = (id) =>
  client.post(`/planning/${id}/topic-intelligence/discard`).then((r) => r.data)
export const resynthesizeTopicIntelligence = (id) =>
  client.post(`/planning/${id}/topic-intelligence/resynthesize`).then((r) => r.data)

// Process notes
export const getProcessNotes = (id) => client.get(`/planning/${id}/process-notes`).then((r) => r.data)
export const putProcessNotes = (id, notes) =>
  client.put(`/planning/${id}/process-notes`, { notes }).then((r) => r.data)

// Scope
export const getScope = (id) => client.get(`/planning/${id}/scope`).then((r) => r.data)
export const updateScope = (id, payload) => client.patch(`/planning/${id}/scope`, payload).then((r) => r.data)
export const addScopeItem = (id, payload) => client.post(`/planning/${id}/scope/items`, payload).then((r) => r.data)
export const updateScopeItem = (itemId, payload) => client.patch(`/scope-items/${itemId}`, payload).then((r) => r.data)
export const deleteScopeItem = (itemId) => client.delete(`/scope-items/${itemId}`).then((r) => r.data)
export const addQuestion = (id, payload) => client.post(`/planning/${id}/scope/questions`, payload).then((r) => r.data)
export const updateQuestion = (qId, payload) => client.patch(`/questions/${qId}`, payload).then((r) => r.data)
export const deleteQuestion = (qId) => client.delete(`/questions/${qId}`).then((r) => r.data)

// ANL
export const getANL = (id) => client.get(`/planning/${id}/anl`).then((r) => r.data)
export const updateANL = (id, payload) => client.patch(`/planning/${id}/anl`, payload).then((r) => r.data)
export const draftANL = (id) => client.post(`/planning/${id}/anl/draft`).then((r) => r.data)
export const reviewANL = (id) => client.post(`/planning/${id}/anl/review`).then((r) => r.data)
export const acceptANLReviews = (id) => client.post(`/planning/${id}/anl/accept-reviews`).then((r) => r.data)
export const updateANLComment = (id, commentId, payload) => client.patch(`/planning/${id}/anl/review-comments/${commentId}`, payload).then((r) => r.data)
export const submitHeadIA = (id) => client.post(`/planning/${id}/anl/submit-head-ia`).then((r) => r.data)
export const headIAApprove = (id) => client.post(`/planning/${id}/anl/head-ia-approve`).then((r) => r.data)
export const markANLSent = (id) => client.post(`/planning/${id}/anl/mark-sent`).then((r) => r.data)

// Frameworks
export const getFrameworkLibrary = (entity) =>
  client.get('/frameworks/library', { params: entity ? { entity } : {} }).then((r) => r.data)
export const addFramework = (id, payload) => client.post(`/planning/${id}/frameworks`, payload).then((r) => r.data)
export const updateFramework = (fwId, payload) => client.patch(`/frameworks/${fwId}`, payload).then((r) => r.data)
export const deleteFramework = (fwId) => client.delete(`/frameworks/${fwId}`).then((r) => r.data)

// Process Understanding agent
export const analyseProcessNotes = (id) =>
  client.post(`/planning/${id}/process-notes/analyse`).then((r) => r.data)
export const approveReasoning = (id, reasoning) =>
  client.post(`/planning/${id}/process-notes/approve-reasoning`, { reasoning }).then((r) => r.data)
export const patchProcessItem = (id, itemId, payload) =>
  client.patch(`/planning/${id}/process-notes/items/${itemId}`, payload).then((r) => r.data)
export const acceptProcessItems = (id, items) =>
  client.post(`/planning/${id}/process-notes/accept`, { items }).then((r) => r.data)

// BRA scope contribution
export const braGenerateScope = (id) =>
  client.post(`/planning/${id}/bra/generate-scope`).then((r) => r.data)
export const braGetScope = (id) =>
  client.get(`/planning/${id}/bra/scope-contribution`).then((r) => r.data)
export const braPublishScope = (id, payload) =>
  client.post(`/planning/${id}/bra/publish-scope`, payload).then((r) => r.data)

// Kickoff scope contribution
export const kickoffGenerateScope = (id) =>
  client.post(`/planning/${id}/kickoff/generate-scope`).then((r) => r.data)
export const kickoffGetScope = (id) =>
  client.get(`/planning/${id}/kickoff/scope-contribution`).then((r) => r.data)
export const kickoffPublishScope = (id, payload) =>
  client.post(`/planning/${id}/kickoff/publish-scope`, payload).then((r) => r.data)

// Phase 3 — Frameworks & Requirements
export const getFrameworkRequirements = (id) =>
  client.get(`/planning/${id}/framework-requirements`).then((r) => r.data)
export const analyseFrameworkRequirements = (id) =>
  client.post(`/planning/${id}/framework-requirements/analyse`).then((r) => r.data)
export const getFrameworkRequirementsStatus = (id) =>
  client.get(`/planning/${id}/framework-requirements/analyse-status`).then((r) => r.data)
export const patchRequirementItem = (id, itemId, payload) =>
  client.patch(`/planning/${id}/framework-requirements/requirements/${itemId}`, payload).then((r) => r.data)
export const acceptFrameworkRequirements = (id) =>
  client.post(`/planning/${id}/framework-requirements/accept`).then((r) => r.data)

// Phase 3 — Supervisory Guidance (sibling of Laws & Regulations, category='guidance')
export const getSupervisoryGuidance = (id) =>
  client.get(`/planning/${id}/supervisory-guidance`).then((r) => r.data)
export const analyseSupervisoryGuidance = (id) =>
  client.post(`/planning/${id}/supervisory-guidance/analyse`).then((r) => r.data)
export const getSupervisoryGuidanceStatus = (id) =>
  client.get(`/planning/${id}/supervisory-guidance/analyse-status`).then((r) => r.data)
export const addSupervisoryGuidance = (id, payload) =>
  client.post(`/planning/${id}/supervisory-guidance`, payload).then((r) => r.data)

// Phase 3 — Resource Planning
export const getResourcePlan = (id) =>
  client.get(`/planning/${id}/resource-plan`).then((r) => r.data)
export const updateResourcePlan = (id, payload) =>
  client.patch(`/planning/${id}/resource-plan`, payload).then((r) => r.data)
export const generateTimeline = (id) =>
  client.post(`/planning/${id}/resource-plan/generate-timeline`).then((r) => r.data)

// Phase 3 — Work Program
export const getWorkProgram = (id) =>
  client.get(`/planning/${id}/work-program`).then((r) => r.data)
export const generateWorkProgram = (id) =>
  client.post(`/planning/${id}/work-program/generate`).then((r) => r.data)
export const patchWorkProgramRow = (id, rowId, payload) =>
  client.patch(`/planning/${id}/work-program/rows/${rowId}`, payload).then((r) => r.data)
export const addWorkProgramRow = (id, payload) =>
  client.post(`/planning/${id}/work-program/add-row`, payload).then((r) => r.data)
export const deleteWorkProgramRow = (id, rowId) =>
  client.delete(`/planning/${id}/work-program/rows/${rowId}`).then((r) => r.data)
export const signOffWorkProgram = (id) =>
  client.post(`/planning/${id}/work-program/sign-off`).then((r) => r.data)
export const reopenWorkProgram = (id) =>
  client.post(`/planning/${id}/work-program/reopen`).then((r) => r.data)

// Framework scope contribution
export const generateFwScope = (id) =>
  client.post(`/planning/${id}/frameworks/generate-scope`).then((r) => r.data)
export const getFwScopeContribution = (id) =>
  client.get(`/planning/${id}/frameworks/scope-contribution`).then((r) => r.data)
export const publishFwScope = (id, payload) =>
  client.post(`/planning/${id}/frameworks/publish-scope`, payload).then((r) => r.data)
