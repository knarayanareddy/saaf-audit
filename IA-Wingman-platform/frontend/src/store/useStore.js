import { create } from 'zustand'

const STORAGE_KEY = 'ia_wingman_current_user'
const AUTH_KEY = 'ia_auth_token'
const THEME_KEY = 'ia_theme'
const CHAT_OPEN_KEY = 'ia_wingman_chat_open'
const SPEAK_REPLIES_KEY = 'ia_wingman_speak_replies'
const NOTIFICATIONS_KEY = 'ia_wingman_notifications_wanted'
const ACTIVE_ENGAGEMENT_KEY = 'ia_wingman_active_engagement'
const VERBOSITY_KEY = 'ia_wingman_chat_verbosity'
const TOUR_VOICE_KEY = 'ia_wingman_tour_voice'
const APP_USERNAME = 'iawingman'

// The assistant's open state is no longer remembered; drop what an earlier version stored.
try { localStorage.removeItem(CHAT_OPEN_KEY) } catch { /* storage unavailable */ }

// Only the fields the sidebar and the chat context need — never the whole
// engagement payload, which can be large and goes stale fast.
const ACTIVE_FIELDS = ['id', 'name', 'audit_code', 'entity', 'status']

function readActiveEngagement() {
  try {
    const raw = localStorage.getItem(ACTIVE_ENGAGEMENT_KEY)
    const eng = raw ? JSON.parse(raw) : null
    return eng && eng.id ? eng : null
  } catch {
    return null
  }
}

function writeActiveEngagement(eng) {
  if (!eng?.id) {
    localStorage.removeItem(ACTIVE_ENGAGEMENT_KEY)
    return
  }
  const slim = Object.fromEntries(ACTIVE_FIELDS.map((k) => [k, eng[k]]))
  localStorage.setItem(ACTIVE_ENGAGEMENT_KEY, JSON.stringify(slim))
}

export const useStore = create((set) => ({
  currentUser: localStorage.getItem(STORAGE_KEY) || null,
  setCurrentUser: (identifier) => {
    localStorage.setItem(STORAGE_KEY, identifier)
    set({ currentUser: identifier })
  },
  clearCurrentUser: () => {
    localStorage.removeItem(STORAGE_KEY)
    sessionStorage.removeItem(AUTH_KEY)
    set({ currentUser: null, authReady: false })
  },

  authReady: !!sessionStorage.getItem(AUTH_KEY),
  // Validate the password against an auth-gated endpoint BEFORE persisting it, so a
  // wrong password shows an error instead of silently bouncing back to this screen.
  // Returns true on success, false on 401. Throws on network failure (backend down).
  setAuth: async (password) => {
    const token = btoa(`${APP_USERNAME}:${password}`)
    const res = await fetch('/api/health', { headers: { Authorization: `Basic ${token}` } })
    if (!res.ok) return false
    sessionStorage.setItem(AUTH_KEY, token)
    set({ authReady: true })
    return true
  },
  clearAuth: () => {
    sessionStorage.removeItem(AUTH_KEY)
    set({ authReady: false })
  },

  // Theme: 'light' | 'dark' | 'system' (persisted; applied by ThemeProvider)
  theme: localStorage.getItem(THEME_KEY) || 'system',
  setTheme: (theme) => {
    localStorage.setItem(THEME_KEY, theme)
    set({ theme })
  },

  // Closed on every load. The open state used to be remembered, so a panel left open once
  // came back on every visit, including the first page after Render woke the service.
  chatOpen: false,
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  setChatOpen: (open) => set({ chatOpen: open }),

  // Off by default — reading every drafted reply aloud is more often
  // annoying than useful; the auditor opts in explicitly.
  speakReplies: localStorage.getItem(SPEAK_REPLIES_KEY) === 'true',
  setSpeakReplies: (on) => {
    localStorage.setItem(SPEAK_REPLIES_KEY, String(on))
    set({ speakReplies: on })
  },

  // The auditor's INTENT — separate from the browser's own Notification.permission,
  // which can be granted/revoked outside this app and is checked live at fire-time.
  notificationsWanted: localStorage.getItem(NOTIFICATIONS_KEY) === 'true',
  setNotificationsWanted: (on) => {
    localStorage.setItem(NOTIFICATIONS_KEY, String(on))
    set({ notificationsWanted: on })
  },

  createEngagementOpen: false,
  setCreateEngagementOpen: (open) => set({ createEngagementOpen: open }),

  paletteOpen: false,
  setPaletteOpen: (open) => set({ paletteOpen: open }),

  // Restored from localStorage on boot so the sidebar can show which audit you
  // are working on straight after a reload.
  activeEngagement: readActiveEngagement(),
  // Never opens the assistant: it used to pop open on every switch of audit and
  // stay open, which auditors found intrusive. The panel opens only when asked.
  setActiveEngagement: (eng) => {
    writeActiveEngagement(eng)
    set({ activeEngagement: eng })
  },
  clearActiveEngagement: () => {
    writeActiveEngagement(null)
    set({ activeEngagement: null })
  },

  // The Play tour narrates itself. On by default — it only ever starts from a
  // deliberate click on Play, and the tour bar carries a mute button right there.
  tourVoice: localStorage.getItem(TOUR_VOICE_KEY) !== 'false',
  setTourVoice: (on) => {
    localStorage.setItem(TOUR_VOICE_KEY, String(on))
    set({ tourVoice: on })
  },

  // Assistant answer length — 'brief' by default; the panel header switches it.
  chatVerbosity: localStorage.getItem(VERBOSITY_KEY) === 'detailed' ? 'detailed' : 'brief',
  setChatVerbosity: (v) => {
    localStorage.setItem(VERBOSITY_KEY, v)
    set({ chatVerbosity: v })
  },

  toast: null,
  showToast: (message, type = 'success') => {
    set({ toast: { message, type } })
    setTimeout(() => set({ toast: null }), 3000)
  },
}))
