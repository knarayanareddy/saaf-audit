// Most-recently-used items for the command palette (localStorage, max 8).
const KEY = 'ia_recent_items'
const MAX = 8

export function getRecents() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function pushRecent(item) {
  if (!item?.id) return
  const list = getRecents().filter((r) => r.id !== item.id)
  list.unshift({ type: item.type, id: item.id, label: item.label, sub: item.sub, route: item.route })
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)))
}
