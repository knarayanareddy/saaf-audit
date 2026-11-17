import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('ia_auth_token')
  if (token) config.headers.Authorization = `Basic ${token}`
  // Who is acting, for the edit register. These are the initials typed at the
  // login screen — self-reported until real sign-in, and the register records
  // them as unverified. Encoded so a name with accents survives the header.
  const actor = localStorage.getItem('ia_wingman_current_user')
  if (actor) config.headers['X-IA-Actor'] = encodeURIComponent(actor)
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('ia_auth_token')
      // Trigger re-auth by resetting Zustand state — import lazily to avoid circular deps
      import('../store/useStore').then(({ useStore }) => {
        useStore.setState({ authReady: false })
      })
    }
    return Promise.reject(error)
  }
)

// Authenticated file download. Goes through the axios client (auth header + 401
// handling) instead of a raw fetch, then triggers a browser download from the blob.
export async function downloadFile(path, fallbackName = 'document') {
  const res = await client.get(path, { responseType: 'blob' })
  const cd = res.headers['content-disposition'] || ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)
  const name = match ? decodeURIComponent(match[1]) : fallbackName
  const url = URL.createObjectURL(res.data)
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default client
