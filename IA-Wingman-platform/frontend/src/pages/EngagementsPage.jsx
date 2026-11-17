import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Pencil, Search, X } from 'lucide-react'
import { getEngagements } from '../api/engagements'
import { useStore } from '../store/useStore'
import { StatusBadge } from '../components/ui/Badge'
import {
  ENTITY_ORDER, AUDIT_TYPES, STATUS_META, entityLabel, auditTypeLabel, ACTIVE_STATUSES,
} from '../lib/entities'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import { SkeletonRow } from '../components/ui/Skeleton'
import { Select, fieldClass } from '../components/ui/Field'
import Toolbar, { FilterChip } from '../components/ui/Toolbar'
import { DataListHeader, DataListRow } from '../components/ui/DataList'
import { Kbd } from '../components/ui/Card'
import EditEngagementModal from '../components/engagement/EditEngagementModal'

// Fixed columns, so the eye reads DOWN a column instead of re-parsing each row.
// Entity is not a column — it is the group heading, exactly as before.
const COLUMNS = [
  { key: 'status', header: 'Status', width: '112px' },
  { key: 'code', header: 'Code', width: '88px', className: 'text-meta' },
  { key: 'name', header: 'Audit', width: 'minmax(0, 1fr)', className: 'font-medium text-fg' },
  { key: 'type', header: 'Type', width: '104px', className: 'text-[13px] text-fg-muted' },
  { key: 'lead', header: 'Lead', width: '132px', className: 'text-[13px] text-fg-muted' },
  { key: 'period', header: 'Period', width: '104px', className: 'text-meta', align: 'right' },
]

export default function EngagementsPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const setCreateEngagementOpen = useStore((s) => s.setCreateEngagementOpen)
  const [editEngagement, setEditEngagement] = useState(null)
  const [search, setSearch] = useState('')
  const searchRef = useRef(null)

  const entity = params.get('entity') || 'all'
  const status = params.get('status') || 'all'
  const type = params.get('type') || null

  const setFilter = (key, value) => {
    const next = new URLSearchParams(params)
    if (!value || value === 'all') next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }

  const { data: engagements = [], isPending } = useQuery({ queryKey: ['engagements'], queryFn: getEngagements })

  // "/" focuses search; Esc clears it.
  useEffect(() => {
    const onKey = (e) => {
      const tag = document.activeElement?.tagName
      if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
        e.preventDefault()
        searchRef.current?.focus()
      } else if (e.key === 'Escape' && document.activeElement === searchRef.current) {
        setSearch('')
        searchRef.current?.blur()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return engagements.filter((e) => {
      if (entity !== 'all' && e.entity !== entity) return false
      if (status === 'active' && !ACTIVE_STATUSES.has(e.status)) return false
      if (status !== 'all' && status !== 'active' && e.status !== status) return false
      if (type && e.audit_type !== type) return false
      if (q) {
        const hay = `${e.name} ${e.audit_code || ''} ${e.lead_auditor || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [engagements, entity, status, type, search])

  const grouped = useMemo(() => {
    const byEntity = {}
    for (const e of filtered) (byEntity[e.entity] ||= []).push(e)
    return ENTITY_ORDER.filter((k) => byEntity[k]?.length).map((k) => ({ entity: k, items: byEntity[k] }))
  }, [filtered])

  const cellsFor = (e) => ({
    status: <StatusBadge status={e.status} />,
    code: e.audit_code || '—',
    name: e.name,
    type: auditTypeLabel(e.audit_type),
    lead: e.lead_auditor || <span className="text-fg-subtle">Unassigned</span>,
    period: e.scope_period || '—',
  })

  return (
    <div className="mx-auto max-w-7xl px-6 py-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-h1 text-fg">Engagements</h1>
          <p className="mt-1 text-[13px] text-fg-muted">
            The audit plan across every entity. Press <Kbd>/</Kbd> to search.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateEngagementOpen(true)}><Plus size={14} /> New engagement</Button>
      </div>

      {/* One control row: search, three filters, and the result count. */}
      <Toolbar
        trailing={
          <span className="text-meta">
            {filtered.length} of {engagements.length}
          </span>
        }
      >
        <div className="relative w-full max-w-xs">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-subtle" />
          <input
            ref={searchRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, code or lead"
            className={fieldClass({ className: 'pl-7 pr-7' })}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-fg-subtle transition-colors duration-150 hover:text-fg"
            >
              <X size={13} />
            </button>
          )}
        </div>

        <Select value={entity} onChange={(e) => setFilter('entity', e.target.value)} aria-label="Filter by entity" className="w-auto">
          <option value="all">All entities</option>
          {ENTITY_ORDER.map((e) => <option key={e} value={e}>{entityLabel(e)}</option>)}
        </Select>

        <Select value={status} onChange={(e) => setFilter('status', e.target.value)} aria-label="Filter by status" className="w-auto">
          <option value="all">All statuses</option>
          <option value="active">Active</option>
          {Object.keys(STATUS_META).map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
        </Select>

        <Select value={type || 'all'} onChange={(e) => setFilter('type', e.target.value === 'all' ? null : e.target.value)} aria-label="Filter by audit type" className="w-auto">
          <option value="all">All types</option>
          {Object.keys(AUDIT_TYPES).map((t) => <option key={t} value={t}>{auditTypeLabel(t)}</option>)}
        </Select>
      </Toolbar>

      {/* Applied filters are echoed only when they are actually narrowing the list. */}
      {(entity !== 'all' || status !== 'all' || type) && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {entity !== 'all' && <FilterChip label="Entity" value={entityLabel(entity)} onClear={() => setFilter('entity', 'all')} />}
          {status !== 'all' && (
            <FilterChip
              label="Status"
              value={status === 'active' ? 'Active' : STATUS_META[status]?.label || status}
              onClear={() => setFilter('status', 'all')}
            />
          )}
          {type && <FilterChip label="Type" value={auditTypeLabel(type)} onClear={() => setFilter('type', null)} />}
        </div>
      )}

      {isPending ? (
        <div className="mt-5 space-y-2">
          <SkeletonRow /><SkeletonRow /><SkeletonRow />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState className="mt-5" icon={Search} title="No engagements match" description="Try clearing a filter or the search term." />
      ) : (
        <div className="mt-5">
          <DataListHeader columns={COLUMNS} />
          {grouped.map(({ entity: ent, items }) => (
            <div key={ent}>
              <div className="flex items-center gap-2 border-b border-line-subtle bg-surface-2/60 px-2 py-1">
                <span className="text-caption">{entityLabel(ent)}</span>
                <span className="text-[11px] tabular-nums text-fg-subtle">{items.length}</span>
              </div>
              <div className="divide-y divide-line-subtle">
                {items.map((e) => (
                  <DataListRow
                    key={e.id}
                    columns={COLUMNS}
                    cells={cellsFor(e)}
                    onClick={() => navigate(`/engagements/${e.id}/planning`)}
                    trailing={
                      <button
                        onClick={(ev) => { ev.stopPropagation(); setEditEngagement(e) }}
                        className="rounded border border-line bg-surface p-1 text-fg-subtle transition-colors duration-150 hover:bg-surface-3 hover:text-fg"
                        title="Edit engagement"
                        aria-label={`Edit ${e.name}`}
                      >
                        <Pencil size={13} />
                      </button>
                    }
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <EditEngagementModal open={!!editEngagement} onClose={() => setEditEngagement(null)} engagement={editEngagement} />
    </div>
  )
}
