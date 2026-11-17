import { useState, useEffect, useRef } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard, FolderKanban, Sparkles, ChevronUp, UserCog, Search, PieChart, Bell, BellOff, Workflow, Bot, X, Pencil,
} from 'lucide-react'
import EditActiveEngagement from '../engagement/EditActiveEngagement'
import { useStore } from '../../store/useStore'
import { useOrg } from '../../lib/useOrg'
import { getCopilotTasks, getReadyForReviewCounts } from '../../api/ai'
import { getEngagements } from '../../api/engagements'
import ThemeToggle from '../theme/ThemeToggle'
import Tooltip from '../ui/Tooltip'

// Workflow leads: it answers "where are we and what happens next", which is the
// question an auditor opens the app with. Dashboard follows as the portfolio view.
const NAV = [
  { to: '/workflow', label: 'Workflow', icon: Workflow, end: false },
  { to: '/agents', label: 'Agents', icon: Bot, end: false },
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/engagements', label: 'Engagements', icon: FolderKanban, end: false },
  { to: '/board', label: 'Board report', icon: PieChart, end: false },
]

// Fires a browser notification per engagement whose ready-for-review count
// just increased, but only while the tab isn't the one the auditor is
// looking at — a visible/focused tab already shows the badge live. Scoped
// deliberately to ready-for-review transitions only (M12's MVP); it does not
// separately watch for proactive chat nudges portfolio-wide — those already
// surface live in that engagement's own open chat panel (M10's poll), and
// watching every engagement's messages for one would mean an N+1 poll this
// endpoint doesn't need to pay for.
function useNotifyOnNewReview(enabled) {
  const navigate = useNavigate()
  const prevRef = useRef(null)
  const { data: counts } = useQuery({
    queryKey: ['copilot-review-counts'],
    queryFn: getReadyForReviewCounts,
    enabled,
    refetchInterval: enabled ? 15000 : false,
  })
  const { data: engagements } = useQuery({ queryKey: ['engagements'], queryFn: getEngagements, enabled })

  useEffect(() => {
    if (!enabled || !counts) return
    const prev = prevRef.current
    prevRef.current = counts
    if (!prev || typeof Notification === 'undefined' || Notification.permission !== 'granted') return
    if (document.visibilityState === 'visible') return
    for (const [engagementId, count] of Object.entries(counts)) {
      if (count > (prev[engagementId] || 0)) {
        const name = engagements?.find((e) => e.id === engagementId)?.name || 'An engagement'
        const n = new Notification('Ready for review', { body: `${name}: ${count} step(s) waiting on you.` })
        n.onclick = () => { window.focus(); navigate(`/engagements/${engagementId}/agents`) }
      }
    }
  }, [enabled, counts, engagements, navigate])
}

// One shape for every row in the rail, so nav links, the assistant toggle and
// the utility rows all sit on the same 32px grid and align on the same icon x.
const ROW = 'flex h-8 w-full items-center gap-2.5 rounded-md px-2 text-[13px] transition-colors duration-150'
const ROW_IDLE = 'text-white/60 hover:bg-white/[0.07] hover:text-white'
const ROW_ACTIVE = 'bg-white/[0.10] font-medium text-white'

export default function LeftSidebar() {
  const org = useOrg()
  const currentUser = useStore((s) => s.currentUser)
  const clearCurrentUser = useStore((s) => s.clearCurrentUser)
  const chatOpen = useStore((s) => s.chatOpen)
  const toggleChat = useStore((s) => s.toggleChat)
  const setPaletteOpen = useStore((s) => s.setPaletteOpen)
  const activeEngagement = useStore((s) => s.activeEngagement)
  const clearActiveEngagement = useStore((s) => s.clearActiveEngagement)
  const notificationsWanted = useStore((s) => s.notificationsWanted)
  const setNotificationsWanted = useStore((s) => s.setNotificationsWanted)
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)

  const isMac = typeof navigator !== 'undefined' && /Mac/.test(navigator.platform)

  const { data: reviewTasks } = useQuery({
    queryKey: ['copilot-tasks', activeEngagement?.id, 'ready_for_review'],
    queryFn: () => getCopilotTasks(activeEngagement.id, 'ready_for_review'),
    enabled: !!activeEngagement?.id,
    refetchInterval: 5000,
  })
  const readyCount = reviewTasks?.length || 0
  // Spelled out rather than left as a bare number: the badge counts AI work that
  // finished and is now waiting on a human decision, for the ACTIVE audit only.
  const reviewHint = `${readyCount} AI ${readyCount === 1 ? 'proposal is' : 'proposals are'} ready for your review`
    + (activeEngagement ? ` in ${activeEngagement.name}` : '')
    + '. Click to open the assistant.'

  useNotifyOnNewReview(notificationsWanted)

  const notificationsSupported = typeof Notification !== 'undefined'
  const toggleNotifications = async () => {
    if (!notificationsSupported) return
    if (!notificationsWanted) {
      const perm = Notification.permission === 'granted' ? 'granted' : await Notification.requestPermission()
      if (perm !== 'granted') return
    }
    setNotificationsWanted(!notificationsWanted)
  }

  return (
    <aside className="flex h-full w-[216px] shrink-0 flex-col bg-sidebar text-white">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2 px-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white/15 text-white">
          <Sparkles size={15} />
        </div>
        <div className="min-w-0 leading-tight">
          <div className="truncate text-[13px] font-semibold tracking-tight">IA Wingman</div>
          <div className="truncate text-[11px] text-white/45">{org.name}</div>
        </div>
      </div>

      {/* Search / command palette trigger */}
      <div className="px-3 pb-2">
        <button
          onClick={() => setPaletteOpen(true)}
          className="flex h-8 w-full items-center gap-2 rounded-md bg-white/[0.07] px-2 text-[13px] text-white/55 transition-colors duration-150 hover:bg-white/[0.12] hover:text-white"
        >
          <Search size={14} className="shrink-0" />
          <span className="flex-1 text-left">Search</span>
          <span className="shrink-0 text-[10px] tracking-wide text-white/35">{isMac ? '⌘K' : 'Ctrl K'}</span>
        </button>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col px-3">
        <div className="space-y-0.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `relative ${ROW} ${isActive ? ROW_ACTIVE : ROW_IDLE}`}>
              {({ isActive }) => (
                <>
                  {/* A 2px marker rather than a filled block: it reads as "you are
                      here" without turning a quarter of the rail into a green slab. */}
                  {isActive && <span className="absolute inset-y-1 left-0 w-0.5 rounded-full bg-brand-light" />}
                  <Icon size={16} className="shrink-0" />
                  {label}
                </>
              )}
            </NavLink>
          ))}

          <button onClick={toggleChat} className={`${ROW} ${chatOpen ? ROW_ACTIVE : ROW_IDLE}`}>
            <Sparkles size={16} className="shrink-0" />
            <span className="flex-1 text-left">AI Assistant</span>
            {readyCount > 0 && (
              <Tooltip side="right" width={200} label={reviewHint}>
                <span
                  aria-label={reviewHint}
                  className="flex h-4 min-w-4 items-center justify-center rounded px-1 text-[10px] font-semibold tabular-nums"
                  style={{ background: 'rgb(var(--sev-med))', color: 'rgb(var(--sidebar))' }}
                >
                  {readyCount}
                </span>
              </Tooltip>
            )}
          </button>
        </div>

        {/* The audit you are working on, shown on every page (not just inside the
            engagement) and restored after a reload, so you never lose your place. */}
        {activeEngagement && (
          <div className="group/active mt-4 border-t border-white/10 pt-3">
            <div className="flex items-start gap-1">
              <button
                onClick={() => navigate(`/engagements/${activeEngagement.id}/planning`)}
                className="min-w-0 flex-1 text-left"
                title={`Open ${activeEngagement.name}`}
              >
                <div className="text-[10px] uppercase tracking-[0.06em] text-white/35">Active engagement</div>
                <div className="mt-0.5 truncate text-[13px] text-white/85 group-hover/active:text-white">
                  {activeEngagement.name}
                </div>
                {activeEngagement.audit_code && (
                  <div className="truncate text-[11px] tabular-nums text-white/40">{activeEngagement.audit_code}</div>
                )}
              </button>
              {/* Always visible, unlike the clear button: it is how you correct a name, code,
                  dates or team, and an option nobody can see is an option nobody has. */}
              <button
                onClick={() => setEditOpen(true)}
                aria-label={`Edit the details of ${activeEngagement.name}`}
                title="Edit name, code, dates and team"
                className="shrink-0 rounded p-0.5 text-white/45 transition duration-150 hover:bg-white/10 hover:text-white/90"
              >
                <Pencil size={12} />
              </button>
              <button
                onClick={clearActiveEngagement}
                aria-label="Clear the active engagement"
                title="Clear the active engagement"
                className="shrink-0 rounded p-0.5 text-white/25 opacity-0 transition duration-150 hover:bg-white/10 hover:text-white/80 focus:opacity-100 group-hover/active:opacity-100"
              >
                <X size={12} />
              </button>
            </div>
          </div>
        )}

        {activeEngagement && (
          <EditActiveEngagement open={editOpen} onClose={() => setEditOpen(false)} engagementId={activeEngagement.id} />
        )}

        {/* Utility rows sit on the same grid as the nav, separated by one hairline
            instead of each living in its own little box. */}
        <div className="mt-auto space-y-0.5 border-t border-white/10 py-2">
          {notificationsSupported && (
            <button
              onClick={toggleNotifications}
              title={notificationsWanted ? 'Notifications on — click to turn off' : 'Get a browser notification when work is ready for review'}
              className={`${ROW} ${ROW_IDLE}`}
            >
              {notificationsWanted ? <Bell size={14} className="shrink-0" /> : <BellOff size={14} className="shrink-0" />}
              <span className="flex-1 text-left text-xs">Notifications</span>
              <span className={`text-[11px] ${notificationsWanted ? 'text-white/70' : 'text-white/30'}`}>
                {notificationsWanted ? 'On' : 'Off'}
              </span>
            </button>
          )}

          <div className={`${ROW} text-white/50`}>
            <span className="flex-1 pl-[26px] text-xs">Theme</span>
            <ThemeToggle tone="onBrand" />
          </div>
        </div>
      </nav>

      {/* Identity footer */}
      <div className="relative border-t border-white/10 px-3 py-2">
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute bottom-full left-3 right-3 z-20 mb-1 overflow-hidden rounded-md border border-line bg-surface-raised shadow-elevated">
              <button
                onClick={() => { setMenuOpen(false); clearCurrentUser() }}
                className="flex w-full items-center gap-2 px-3 py-2 text-[13px] text-fg hover:bg-surface-3"
              >
                <UserCog size={14} className="text-fg-subtle" />
                Change identity
              </button>
            </div>
          </>
        )}
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className={`${ROW} ${ROW_IDLE}`}
          title="Click to change identity"
        >
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-white/15 text-[10px] font-semibold text-white">
            {currentUser || '—'}
          </span>
          <span className="flex-1 text-left text-xs">Signed in</span>
          <ChevronUp size={13} className={`shrink-0 transition-transform duration-150 ${menuOpen ? '' : 'rotate-180'}`} />
        </button>
      </div>
    </aside>
  )
}
