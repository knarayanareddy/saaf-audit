import {
  AlertTriangle, BarChart3, CalendarDays, ClipboardCheck, Compass, Cpu, FileCheck2,
  FileText, FileWarning, FolderSearch, Gavel, Inbox, LayoutGrid, LayoutList, ListChecks,
  Lock, Mail, MessagesSquare, Mic, Network, PenLine, Radar, Scale, ScanSearch,
  ShieldQuestion, Sparkles, Table2, Target, User, Users,
} from 'lucide-react'

// The frontend half of the agent registry (backend: services/agent_registry.py).
//
// The backend sends an icon NAME, not a component, and this map turns it into
// one. Explicitly, by hand: `lucide[name]` would work at runtime and defeat
// tree-shaking, pulling every icon in the library into the bundle, and a typo
// would render nothing at all rather than failing anywhere a person would see.
// Here a missing name falls back visibly and `tests/agents.test.mjs` fails.
const ICONS = {
  AlertTriangle, BarChart3, CalendarDays, ClipboardCheck, Compass, FileCheck2, FileText,
  FileWarning, FolderSearch, Gavel, Inbox, LayoutGrid, LayoutList, ListChecks, Lock, Mail,
  MessagesSquare, Mic, Network, PenLine, Radar, Scale, ScanSearch, ShieldQuestion,
  Table2, Target, Users,
}

export const ICON_NAMES = Object.keys(ICONS)

/** The component for an icon name, or a neutral mark when it is unknown. */
export function agentIcon(name) {
  return ICONS[name] || Sparkles
}

// What an agent IS, which the platform used to conflate. "Agent" was applied to
// Fieldwork (a person typing), to Resource Planning (a form) and to the coverage
// check (a computed view with nothing to run). Three marks, three meanings.
export const KINDS = {
  agent: {
    label: 'AI proposes',
    icon: Sparkles,
    cls: 'text-brand',
    hint: 'An AI model drafts or proposes here; you decide what counts. Each run uses the model and costs a little.',
  },
  engine: {
    label: 'Computed',
    icon: Cpu,
    cls: 'text-fg-muted',
    hint: 'Calculated by fixed rules — no model, no judgement, no cost.',
  },
  'your step': {
    label: 'Your step',
    icon: User,
    cls: 'text-fg-subtle',
    hint: 'You do this. The platform holds the result; it does not produce it.',
  },
}

export function kindMeta(kind) {
  return KINDS[kind] || KINDS.agent
}

/**
 * Index a catalog by key AND by every alias, so any name a layer has ever used
 * for an agent resolves to the same row.
 */
export function indexAgents(agents = []) {
  const byKey = {}
  for (const a of agents) {
    byKey[a.key] = a
    for (const alias of a.aliases || []) byKey[alias] = a
  }
  return byKey
}

/**
 * A name fit to show a person, never a raw key. An unregistered agent reads as
 * "Some new agent" rather than as `some_new_agent` — the activity log showed
 * people the second kind for months.
 */
export function agentName(key, index = {}) {
  const found = index[key]
  if (found) return found.name
  if (!key) return 'Unknown agent'
  return key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}
