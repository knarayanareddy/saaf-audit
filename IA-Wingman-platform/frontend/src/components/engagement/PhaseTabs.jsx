import { useNavigate } from 'react-router-dom'
import { Workflow } from 'lucide-react'

// The engagement phase strip. One shared source of truth for the phase order so
// Planning and Quality (and any future phase page) render an identical nav.
const PHASES = [
  { key: 'planning', label: 'Planning', route: 'planning' },
  { key: 'fieldwork', label: 'Fieldwork', route: 'fieldwork' },
  { key: 'reporting', label: 'Reporting', route: 'reporting' },
  { key: 'quality', label: 'Quality', route: 'quality' },
  { key: 'documents', label: 'Documents', route: 'documents' },
]

export default function PhaseTabs({ engagementId, active }) {
  const navigate = useNavigate()
  return (
    <div className="mt-4 flex gap-4 border-b border-line text-sm">
      {PHASES.map((p) =>
        p.key === active ? (
          <span key={p.key} className="border-b-2 border-brand pb-2 font-medium text-brand">
            {p.label}
          </span>
        ) : (
          <button
            key={p.key}
            onClick={() => navigate(`/engagements/${engagementId}/${p.route}`)}
            className="pb-2 text-fg-muted hover:text-brand"
          >
            {p.label}
          </button>
        ),
      )}
      <button
        onClick={() => navigate(`/workflow?engagement=${engagementId}`)}
        className="ml-auto inline-flex items-center gap-1.5 pb-2 text-fg-muted hover:text-brand"
      >
        <Workflow size={14} /> Workflow
      </button>
    </div>
  )
}
