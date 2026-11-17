import client, { downloadFile } from './client'

export const runAgents = (id, payload) =>
  client.post(`/engagements/${id}/agents/run`, payload).then((r) => r.data)
export const runAgentsV2 = (id, payload) =>
  client.post(`/engagements/${id}/agents/run-v2`, payload).then((r) => r.data)
export const getAgentsStatus = (id) =>
  client.get(`/engagements/${id}/agents/status`).then((r) => r.data)
export const getActivity = (id) =>
  client.get(`/engagements/${id}/activity`).then((r) => r.data)
export const getAgentRuns = (id) =>
  client.get(`/engagements/${id}/agents/runs`).then((r) => r.data)
export const getAgentPack = (id) =>
  client.get(`/engagements/${id}/agents/pack`).then((r) => r.data)
export const getAgentCatalog = () =>
  client.get('/agents/catalog').then((r) => r.data)
export const getAgentSpend = (id) =>
  client.get(`/engagements/${id}/agents/spend`).then((r) => r.data)

export const uploadDocument = (id, file) => {
  const form = new FormData()
  form.append('file', file)
  // Let the browser set Content-Type so it includes the multipart boundary.
  // Hardcoding 'multipart/form-data' omits the boundary → 400 "Missing boundary".
  return client.post(`/engagements/${id}/documents`, form).then((r) => r.data)
}
export const listDocuments = (id) => client.get(`/engagements/${id}/documents`).then((r) => r.data)
export const deleteDocument = (docId) => client.delete(`/documents/${docId}`).then((r) => r.data)
export const getDocument = (docId) => client.get(`/documents/${docId}`).then((r) => r.data)
export const updateDocument = (docId, extracted_text) =>
  client.patch(`/documents/${docId}`, { extracted_text }).then((r) => r.data)
export const downloadDocument = (docId, filename) =>
  downloadFile(`/documents/${docId}/download`, filename)
