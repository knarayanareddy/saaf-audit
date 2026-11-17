import client, { downloadFile } from './client'

// Findings (5C)
export const listFindings = (id) =>
  client.get(`/reporting/${id}/findings`).then((r) => r.data)
export const seedFindings = (id) =>
  client.post(`/reporting/${id}/findings/seed-from-fieldwork`).then((r) => r.data)
export const createFinding = (id, payload) =>
  client.post(`/reporting/${id}/findings`, payload).then((r) => r.data)
export const updateFinding = (id, fid, payload) =>
  client.patch(`/reporting/${id}/findings/${fid}`, payload).then((r) => r.data)
export const deleteFinding = (id, fid) =>
  client.delete(`/reporting/${id}/findings/${fid}`).then((r) => r.data)
export const draftFinding = (id, fid) =>
  client.post(`/reporting/${id}/findings/${fid}/draft`).then((r) => r.data)

// Explainability annex
export const getExplainability = (id, fid) =>
  client.get(`/reporting/${id}/findings/${fid}/explainability`).then((r) => r.data)
export const sharpenExplainability = (id, fid) =>
  client.post(`/reporting/${id}/findings/${fid}/explainability/sharpen`).then((r) => r.data)

// Grounded validator — re-reads the source per claim (found + verbatim quote)
export const getValidation = (id, fid) =>
  client.get(`/reporting/${id}/findings/${fid}/validation`).then((r) => r.data)
export const judgeValidation = (id, fid) =>
  client.post(`/reporting/${id}/findings/${fid}/validation/judge`).then((r) => r.data)

// Report
export const getReport = (id) =>
  client.get(`/reporting/${id}/report`).then((r) => r.data)
export const draftReport = (id) =>
  client.post(`/reporting/${id}/report/draft`).then((r) => r.data)
export const updateReport = (id, payload) =>
  client.patch(`/reporting/${id}/report`, payload).then((r) => r.data)
export const exportReport = (id) =>
  downloadFile(`/reporting/${id}/report/export-word`, 'Audit-Report.docx')
