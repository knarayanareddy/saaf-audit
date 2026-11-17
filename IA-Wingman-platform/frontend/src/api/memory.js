import client from './client'

// Audit Memory — deterministic cross-engagement recall + adopt + opt-in synthesis.
export const getRecall = (id) =>
  client.get(`/memory/${id}/recall`).then((r) => r.data)
export const adoptPrecedent = (id, payload) =>
  client.post(`/memory/${id}/adopt`, payload).then((r) => r.data)
export const synthesizeMemory = (id) =>
  client.post(`/memory/${id}/synthesize`).then((r) => r.data)
