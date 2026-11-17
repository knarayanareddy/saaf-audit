import client from './client'

// The edit register: who proposed a record and who decided about it. Read-only —
// the backend records changes itself; there is nothing to write from here.
export const getHistory = (entity, entityId) =>
  client.get(`/history/${entity}/${entityId}`).then((r) => r.data)

// How much of an audit file IA Wingman proposed, and what people did with it.
export const getAiShare = (engagementId) =>
  client.get(`/engagements/${engagementId}/ai-share`).then((r) => r.data)
