import client, { downloadFile } from './client'

export const getGeneratedDocuments = (id) =>
  client.get(`/engagements/${id}/documents/generated`).then((r) => r.data)

// The catalogue returns each document's own authenticated export path.
export const downloadDocument = (path, filename) => downloadFile(path, filename)
