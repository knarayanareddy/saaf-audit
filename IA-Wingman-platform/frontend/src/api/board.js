import client, { downloadFile } from './client'

// Board / portfolio report — deterministic aggregates + optional AI narrative.
export const getBoardSummary = () =>
  client.get('/board/summary').then((r) => r.data)
export const getBoardNarrative = () =>
  client.get('/board/narrative').then((r) => r.data)
export const draftBoardNarrative = () =>
  client.post('/board/narrative/draft').then((r) => r.data)
export const exportBoard = () =>
  downloadFile('/board/export-word', 'Board-Report.docx')
