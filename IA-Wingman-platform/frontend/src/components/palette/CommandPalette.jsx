import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search, FolderKanban, FileText, LayoutDashboard, Plus, Sparkles,
  MoonStar, CornerDownLeft, Clock, Workflow,
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import { getEngagements } from '../../api/engagements'
import { entityLabel, statusLabel } from '../../lib/entities'
import { fuzzyScore } from '../../lib/fuzzy'
import { getRecents, pushRecent } from '../../lib/recents'

const MODULES = [
  { route: 'topic-intelligence', label: 'Topic Intelligence' },
  { route: 'process-understanding', label: 'Process Understanding' },
  { route: 'framework-requirements', label: 'Laws & Regulations' },
  { route: 'supervisory-guidance', label: 'Supervisory Guidance' },
  { route: 'scope-objectives', label: 'Scope & Objectives' },
  { route: 'anl', label: 'Audit Notification Letter' },
  { route: 'kickoff', label: 'Kick-off Agenda' },
  { route: 'bra', label: 'Background Risk Assessment' },
  { route: 'resource-plan', label: 'Resource Plan' },
  { route: 'work-program', label: 'Work Program' },
  { route: 'drl', label: 'Document Request List' },
]

const TYPE_ICON = { engagement: FolderKanban, module: FileText, action: Sparkles }

export default function CommandPalette() {
  const open = useStore((s) => s.paletteOpen)
  const setOpen = useStore((s) => s.setPaletteOpen)
  const setCreateEngagementOpen = useStore((s) => s.setCreateEngagementOpen)
  const toggleChat = useStore((s) => s.toggleChat)
  const theme = useStore((s) => s.theme)
  const setTheme = useStore((s) => s.setTheme)
  const navigate = useNavigate()

  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  const { data: engagements = [] } = useQuery({
    queryKey: ['engagements'],
    queryFn: getEngagements,
    enabled: open,
  })

  // Global ⌘K / Ctrl+K to toggle the palette.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(!useStore.getState().paletteOpen)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setOpen])

  useEffect(() => {
    if (open) {
      setQuery('')
      setActive(0)
      setTimeout(() => inputRef.current?.focus(), 20)
    }
  }, [open])

  const actions = useMemo(() => [
    { type: 'action', id: 'act:new', label: 'New engagement', sub: 'Create', icon: Plus, run: () => setCreateEngagementOpen(true) },
    { type: 'action', id: 'act:workflow', label: 'Go to Workflow', sub: 'Navigate', icon: Workflow, route: '/workflow' },
    { type: 'action', id: 'act:dashboard', label: 'Go to Dashboard', sub: 'Navigate', icon: LayoutDashboard, route: '/' },
    { type: 'action', id: 'act:engagements', label: 'Go to Engagements', sub: 'Navigate', icon: FolderKanban, route: '/engagements' },
    { type: 'action', id: 'act:ai', label: 'Toggle AI Assistant', sub: 'Panel', icon: Sparkles, run: () => toggleChat() },
    { type: 'action', id: 'act:theme', label: 'Toggle dark mode', sub: 'Theme', icon: MoonStar, run: () => setTheme(theme === 'dark' ? 'light' : 'dark') },
  ], [setCreateEngagementOpen, toggleChat, setTheme, theme])

  const index = useMemo(() => {
    const engEntries = engagements.map((e) => ({
      type: 'engagement',
      id: `eng:${e.id}`,
      label: e.name,
      sub: [e.audit_code, entityLabel(e.entity), statusLabel(e.status)].filter(Boolean).join(' · '),
      route: `/engagements/${e.id}/planning`,
      keywords: `${e.name} ${e.audit_code || ''} ${entityLabel(e.entity)} ${statusLabel(e.status)} ${e.audit_type}`,
    }))
    const modEntries = engagements.flatMap((e) =>
      MODULES.map((m) => ({
        type: 'module',
        id: `mod:${e.id}:${m.route}`,
        label: `${e.name} — ${m.label}`,
        sub: 'Planning module',
        route: `/engagements/${e.id}/planning/${m.route}`,
        keywords: `${e.name} ${m.label}`,
      })),
    )
    return { engEntries, modEntries }
  }, [engagements])

  const results = useMemo(() => {
    const q = query.trim()
    if (!q) {
      const recents = getRecents()
      return [...recents.map((r) => ({ ...r, isRecent: true })), ...actions]
    }
    const pool = [...index.engEntries, ...actions]
    // Module entries only join once the query is specific enough (≥2 chars).
    if (q.length >= 2) pool.push(...index.modEntries)
    return pool
      .map((item) => ({ item, score: fuzzyScore(q, `${item.label} ${item.keywords || item.sub || ''}`) }))
      .filter((r) => r.score > -Infinity)
      .sort((a, b) => b.score - a.score)
      .slice(0, 12)
      .map((r) => r.item)
  }, [query, index, actions])

  useEffect(() => { setActive(0) }, [query])
  useEffect(() => {
    listRef.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
  }, [active, results])

  if (!open) return null

  const select = (item) => {
    if (!item) return
    if (item.route) navigate(item.route)
    if (item.run) item.run()
    if (item.type === 'engagement' || item.type === 'module') {
      pushRecent({ type: item.type, id: item.id, label: item.label, sub: item.sub, route: item.route })
    }
    setOpen(false)
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); select(results[active]) }
    else if (e.key === 'Escape') { e.preventDefault(); setOpen(false) }
  }

  const showingRecents = !query.trim()

  return (
    <div
      className="fixed inset-0 z-[70] flex items-start justify-center bg-black/40 p-4 pt-[12vh] animate-fade-in"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-line bg-surface shadow-elevated animate-scale-in"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Command palette"
      >
        <div className="flex items-center gap-2 border-b border-line px-4">
          <Search size={18} className="shrink-0 text-fg-subtle" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search engagements, modules, actions…"
            className="w-full bg-transparent py-3.5 text-sm text-fg outline-none placeholder:text-fg-subtle"
          />
        </div>

        <div ref={listRef} className="max-h-[52vh] overflow-y-auto p-2" role="listbox">
          {showingRecents && results.length > 0 && (
            <div className="px-2 py-1 text-caption text-fg-subtle">
              {getRecents().length ? 'Recent & actions' : 'Actions'}
            </div>
          )}
          {results.length === 0 && (
            <div className="px-3 py-10 text-center text-sm text-fg-muted">No matches for “{query}”.</div>
          )}
          {results.map((item, i) => {
            const Icon = item.icon || TYPE_ICON[item.type] || FileText
            const isActive = i === active
            return (
              <button
                key={item.id}
                data-active={isActive}
                role="option"
                aria-selected={isActive}
                onMouseEnter={() => setActive(i)}
                onClick={() => select(item)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                  isActive ? 'bg-brand-subtle' : 'hover:bg-surface-3'
                }`}
              >
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${isActive ? 'bg-brand text-brand-fg' : 'bg-surface-3 text-fg-muted'}`}>
                  {item.isRecent ? <Clock size={15} /> : <Icon size={15} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-fg">{item.label}</span>
                  {item.sub && <span className="block truncate text-xs text-fg-subtle">{item.sub}</span>}
                </span>
                {isActive && <CornerDownLeft size={14} className="shrink-0 text-fg-subtle" />}
              </button>
            )
          })}
        </div>

        <div className="flex items-center justify-between border-t border-line px-4 py-2 text-[11px] text-fg-subtle">
          <span>↑↓ navigate · ↵ open · esc close</span>
          <span>{results.length} result{results.length === 1 ? '' : 's'}</span>
        </div>
      </div>
    </div>
  )
}
