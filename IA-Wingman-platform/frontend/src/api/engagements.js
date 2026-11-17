import client from './client'

export const getEngagements = () => client.get('/engagements').then((r) => r.data)
export const getEngagementStats = () => client.get('/engagements/stats').then((r) => r.data)
export const getEngagement = (id) => client.get(`/engagements/${id}`).then((r) => r.data)
export const createEngagement = (payload) => client.post('/engagements', payload).then((r) => r.data)
export const updateEngagement = (id, payload) => client.patch(`/engagements/${id}`, payload).then((r) => r.data)
export const deleteEngagement = (id) => client.delete(`/engagements/${id}`).then((r) => r.data)
export const suggestSummary = (payload) => client.post('/ai/suggest-summary', payload).then((r) => r.data)
