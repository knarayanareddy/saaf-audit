import client from './client'

// Chat is a POST that streams SSE. EventSource only supports GET, so we read the
// stream manually with fetch + getReader and parse the SSE frames ourselves.
export async function streamChat({ messages, engagementId, verbosity }, { onDelta, onAction, onComplete, onError }) {
  try {
    const token = sessionStorage.getItem('ia_auth_token')
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Basic ${token}` } : {}),
      },
      body: JSON.stringify({ messages, engagement_id: engagementId || null, verbosity: verbosity || 'brief' }),
    })
    if (!res.ok || !res.body) {
      if (res.status === 401 || res.status === 500) {
        onError?.('API key not configured. Add your ANTHROPIC_API_KEY to backend/.env and restart the backend.')
      } else {
        onError?.(`The AI service is unavailable (HTTP ${res.status}).`)
      }
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split('\n\n')
      buffer = frames.pop()
      for (const frame of frames) {
        const eventMatch = frame.match(/^event: (.+)$/m)
        const dataMatch = frame.match(/^data: (.+)$/m)
        if (!dataMatch) continue
        let payload
        try {
          payload = JSON.parse(dataMatch[1])
        } catch {
          continue
        }
        const evt = eventMatch?.[1]
        if (evt === 'delta') onDelta?.(payload.text)
        else if (evt === 'action') onAction?.(payload)
        else if (evt === 'complete') onComplete?.(payload.content)
        else if (evt === 'error') onError?.(payload.message)
      }
    }
  } catch (err) {
    onError?.('Connection error.')
  }
}

export const getCopilotMessages = (engagementId) =>
  client.get(`/copilot/${engagementId}/messages`).then((r) => r.data)
export const patchCopilotProposal = (proposalId, status) =>
  client.patch(`/copilot/proposals/${proposalId}`, { status }).then((r) => r.data)
export const runCopilotStage = (engagementId, stageKey) =>
  client.post(`/copilot/${engagementId}/stages/${stageKey}/run`).then((r) => r.data)
export const getCopilotTasks = (engagementId, status) =>
  client.get(`/copilot/${engagementId}/tasks`, { params: status ? { status } : {} }).then((r) => r.data)
export const patchCopilotTask = (taskId, status) =>
  client.patch(`/copilot/tasks/${taskId}`, { status }).then((r) => r.data)
export const setCopilotAutonomy = (engagementId, paused) =>
  client.patch(`/copilot/${engagementId}/autonomy`, { paused }).then((r) => r.data)
export const getReadyForReviewCounts = () =>
  client.get('/copilot/ready-for-review-counts').then((r) => r.data)

export const suggestName = (payload) => client.post('/ai/suggest-name', payload).then((r) => r.data)
export const suggestObjective = (engagementId) =>
  client.post(`/ai/suggest-objective/${engagementId}`).then((r) => r.data)
export const improveText = (payload) => client.post('/ai/improve-text', payload).then((r) => r.data)
