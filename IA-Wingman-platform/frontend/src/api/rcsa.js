import client from './client'

// The RCSA import. Four steps in order — upload, look at the sheet, confirm what
// each column holds, read the rows — plus the reliance decision, which is what
// has to exist before any of it may be leaned on.

export const uploadRcsa = (engagementId, file) => {
  const form = new FormData()
  form.append('file', file)
  return client
    .post(`/engagements/${engagementId}/rcsa/imports`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const previewRcsa = (importId, sheet) =>
  client.get(`/rcsa/imports/${importId}/preview`, { params: sheet ? { sheet } : {} })
    .then((r) => r.data)

export const proposeMapping = (importId, body) =>
  client.post(`/rcsa/imports/${importId}/propose`, body).then((r) => r.data)

export const confirmMapping = (importId, body) =>
  client.post(`/rcsa/imports/${importId}/confirm`, body).then((r) => r.data)

export const reprojectRcsa = (importId) =>
  client.post(`/rcsa/imports/${importId}/reproject`).then((r) => r.data)

export const listRcsaImports = (engagementId) =>
  client.get(`/engagements/${engagementId}/rcsa/imports`).then((r) => r.data)

export const getRcsaRows = (importId) =>
  client.get(`/rcsa/imports/${importId}/rows`).then((r) => r.data)

export const getReliance = (importId) =>
  client.get(`/rcsa/imports/${importId}/reliance`).then((r) => r.data)

export const recordReliance = (importId, body) =>
  client.post(`/rcsa/imports/${importId}/reliance`, body).then((r) => r.data)

export const defaultSelection = (importId) =>
  client.get(`/rcsa/imports/${importId}/default-selection`).then((r) => r.data)

export const proposeRisks = (importId, rowIds) =>
  client.post(`/rcsa/imports/${importId}/propose-risks`, { row_ids: rowIds }).then((r) => r.data)
