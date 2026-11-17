import client, { downloadFile } from './client'

// Interview Agent v2 — persona guide
export const getGuide = (id) =>
  client.get(`/planning/${id}/interview/guide`).then((r) => r.data)
export const buildGuide = (id) =>
  client.post(`/planning/${id}/interview/guide`).then((r) => r.data)

// Live Companion — sessions
export const listSessions = (id) =>
  client.get(`/planning/${id}/interview/sessions`).then((r) => r.data)
export const createSession = (id, payload) =>
  client.post(`/planning/${id}/interview/sessions`, payload).then((r) => r.data)
export const updateSession = (id, sid, payload) =>
  client.patch(`/planning/${id}/interview/sessions/${sid}`, payload).then((r) => r.data)
export const deleteSession = (id, sid) =>
  client.delete(`/planning/${id}/interview/sessions/${sid}`).then((r) => r.data)
export const analyseSession = (id, sid) =>
  client.post(`/planning/${id}/interview/sessions/${sid}/analyse`).then((r) => r.data)
export const exportMinutes = (id, sid) =>
  downloadFile(`/planning/${id}/interview/sessions/${sid}/minutes`, 'Interview-Minutes.docx')
