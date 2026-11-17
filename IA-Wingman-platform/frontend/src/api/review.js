import client from './client'

export const getReview = (id, artifact) =>
  client.get(`/planning/${id}/review/${artifact}`).then((r) => r.data)
export const runReview = (id, artifact, phase = 'total') =>
  client.post(`/planning/${id}/review/${artifact}`, null, { params: { phase } }).then((r) => r.data)
export const patchReviewComment = (id, artifact, commentId, payload) =>
  client.patch(`/planning/${id}/review/${artifact}/comments/${commentId}`, payload).then((r) => r.data)
export const getCoverage = (id) =>
  client.get(`/planning/${id}/coverage`).then((r) => r.data)
