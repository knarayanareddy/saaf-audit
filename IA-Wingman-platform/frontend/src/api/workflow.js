import client from './client'

export const getWorkflowMethod = () => client.get('/workflow/method').then((r) => r.data)
export const getEngagementWorkflow = (id) => client.get(`/workflow/${id}`).then((r) => r.data)
