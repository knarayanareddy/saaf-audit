import client from './client'

export const getPosture = () => client.get('/assurance/posture').then((r) => r.data)
export const getRuns = () => client.get('/assurance/runs').then((r) => r.data)
export const getRunDetail = (id) => client.get(`/assurance/runs/${id}`).then((r) => r.data)
export const getDocumentFlags = () => client.get('/assurance/documents/flags').then((r) => r.data)

// mode: 'static' (free, deterministic) | 'live' (opt-in, spends AI budget — needs confirm token)
export const runSuite = (mode, confirm) =>
  client.post('/assurance/suite/run', { mode, confirm }).then((r) => r.data)

export const LIVE_CONFIRM_TOKEN = 'RUN-LIVE'
