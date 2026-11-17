import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { getHistory } from '../../api/history'

// Who proposed this record and who decided about it, from the backend's
// append-only edit register. Loaded only when opened: a page of fifty records
// should not fetch fifty histories nobody asked for.
const DECISION_LABEL = {
  proposed: 'proposed', created: 'created', modified: 'changed', accepted: 'accepted',
  rejected: 'rejected', superseded: 'replaced by a re-run', deleted: 'deleted',
}

function shortValue(v) {
  if (v == null || v === '') return '—'
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 80 ? `${s.slice(0, 80)}…` : s
}

export default function RecordHistory({ entity, entityId, className = 'mt-4 border-t border-line pt-3' }) {
  const [open, setOpen] = useState(false)
  const { data, isPending, isError } = useQuery({
    queryKey: ['history', entity, entityId],
    queryFn: () => getHistory(entity, entityId),
    enabled: open && !!entityId,
  })
  const rows = data?.rows || []

  if (!entityId) return null

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-caption font-semibold uppercase tracking-wide text-fg-subtle hover:text-fg"
      >
        History
        <ChevronRight size={13} className={open ? 'rotate-90 transition' : 'transition'} />
      </button>
      {open && (
        <div className="mt-2 space-y-2 text-sm">
          {isPending && <p className="text-caption text-fg-subtle">Loading…</p>}
          {isError && <p className="text-caption text-sev-high">The history could not be loaded.</p>}
          {!isPending && !isError && rows.length === 0 && (
            <p className="text-caption text-fg-subtle">
              Nothing recorded for this item.
              {data?.recorded_since && ` The register has kept records since ${new Date(data.recorded_since).toLocaleDateString()}; this item may be older.`}
            </p>
          )}
          {rows.map((r, i) => (
            <div key={i} className="rounded-lg bg-surface-2 px-3 py-2">
              <div className="flex flex-wrap items-center gap-x-2 text-caption text-fg-subtle">
                <span className="font-semibold text-fg">{DECISION_LABEL[r.decision] || r.decision}</span>
                {r.field !== '*' && <span>· {r.field}</span>}
                <span>· {r.actor_kind === 'ai' ? `AI (${r.actor})` : r.actor}</span>
                {r.actor_kind === 'human' && !r.actor_verified && (
                  <span title="Initials typed at sign-in; there is no verified login yet">· unverified</span>
                )}
                {r.at && <span>· {new Date(r.at).toLocaleString()}</span>}
              </div>
              {(r.decision === 'modified' || (r.decision === 'proposed' && r.before != null)) && (
                <div className="mt-1 text-caption text-fg-muted">
                  <span className="line-through">{shortValue(r.before)}</span> → <span className="text-fg">{shortValue(r.after)}</span>
                </div>
              )}
              {r.run && (
                <div className="mt-1 text-caption text-fg-subtle">
                  {r.run.linked
                    ? `${r.run.models.join(', ')} · prompt ${r.run.prompt_versions.join(', ') || 'not recorded'}`
                    : 'Run not linked to the ledger — the model that wrote this cannot be named'}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
