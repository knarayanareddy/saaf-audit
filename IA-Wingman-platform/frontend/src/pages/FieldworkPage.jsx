import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Plus, Trash2, Sparkles, Lock, AlertTriangle,
  ThumbsUp, ArrowUpCircle, Lightbulb, Edit2, Check, X,
} from 'lucide-react'
import client from '../api/client'
import Button from '../components/ui/Button'
import { SectionHeading } from '../components/ui/Card'
import GovernanceAssessorPanel from '../components/racm/GovernanceAssessorPanel'
import DataAnalysisPanel from '../components/racm/DataAnalysisPanel'
import PrivacyGuardPanel from '../components/racm/PrivacyGuardPanel'
import VendorGuardPanel from '../components/racm/VendorGuardPanel'
import EvidenceChasePanel from '../components/racm/EvidenceChasePanel'
import { useStore } from '../store/useStore'
import Tooltip from '../components/ui/Tooltip'

const getObs = (id) => client.get(`/fieldwork/${id}/observations`).then((r) => r.data)
const seedObs = (id) => client.post(`/fieldwork/${id}/observations/seed-from-planning`).then((r) => r.data)
const createObs = (id, payload) => client.post(`/fieldwork/${id}/observations`, payload).then((r) => r.data)
const patchObs = (id, obsId, payload) => client.patch(`/fieldwork/${id}/observations/${obsId}`, payload).then((r) => r.data)
const deleteObs = (id, obsId) => client.delete(`/fieldwork/${id}/observations/${obsId}`).then((r) => r.data)

const TABS = [
  { key: 'findings', label: 'Findings', icon: AlertTriangle, color: 'text-sev-high', obsType: 'finding' },
  { key: 'recommendations', label: 'Recommendations', icon: ArrowUpCircle, color: 'text-sev-med', obsType: 'recommendation' },
  { key: 'good_practices', label: 'Good Practice', icon: ThumbsUp, color: 'text-sev-low', obsType: 'good_practice' },
  { key: 'improvements', label: 'Ongoing Improvement', icon: Lightbulb, color: 'text-blue-600', obsType: 'improvement' },
]

const SOURCE_BADGE = {
  'Process Understanding': 'bg-violet-100 text-violet-700',
  'Work Program': 'bg-brand-subtle text-brand',
  'Manual': 'bg-surface-3 text-fg-muted',
}

function ObsRow({ obs, engagementId, onPatch, onDelete }) {
  const [editing, setEditing] = useState(null) // field name being edited
  const [draft, setDraft] = useState('')

  const startEdit = (field, value) => { setEditing(field); setDraft(value || '') }
  const saveEdit = (field) => {
    onPatch(obs.id, { [field]: draft })
    setEditing(null)
  }

  const cell = (field, value, multiline = false) => {
    if (editing === field) {
      return multiline
        ? <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => saveEdit(field)}
            autoFocus
            rows={3}
            className="w-full resize-none rounded border border-brand px-2 py-1 text-xs outline-none"
          />
        : <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => saveEdit(field)}
            autoFocus
            className="w-full rounded border border-brand px-2 py-1 text-xs outline-none"
          />
    }
    return (
      <div
        onClick={() => startEdit(field, value)}
        className="cursor-pointer rounded px-1 py-0.5 text-xs hover:bg-surface-3"
      >
        {value || <span className="italic text-fg-subtle">Click to add…</span>}
      </div>
    )
  }

  const srcBadge = SOURCE_BADGE[obs.source] || SOURCE_BADGE.Manual

  return (
    <tr className="border-b border-line align-top hover:bg-surface-3/50">
      <td className="px-3 py-3 min-w-[160px]">
        <div className="flex flex-col gap-1">
          {cell('title', obs.title)}
          <div className="flex gap-1 flex-wrap">
            {obs.source && (
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${srcBadge}`}>
                {obs.source}
              </span>
            )}
            {obs.is_ai_generated && (
              <span className="flex items-center gap-0.5 rounded bg-violet-50 px-1.5 py-0.5 text-[10px] font-semibold text-violet-600">
                <Sparkles size={8} /> AI
              </span>
            )}
          </div>
        </div>
      </td>
      <td className="px-3 py-3 w-[120px]">{cell('criteria', obs.criteria, true)}</td>
      <td className="px-3 py-3 min-w-[180px]">{cell('detailed_observation', obs.detailed_observation, true)}</td>
      <td className="px-3 py-3 w-[130px]">{cell('root_cause', obs.root_cause, true)}</td>
      <td className="px-3 py-3 w-[130px]">{cell('risk', obs.risk, true)}</td>
      <td className="px-3 py-3 w-8">
        <Tooltip label="Delete observation" side="left">
          <button onClick={() => onDelete(obs.id)} aria-label="Delete observation" className="text-fg-subtle hover:text-sev-high">
            <Trash2 size={13} />
          </button>
        </Tooltip>
      </td>
    </tr>
  )
}

export default function FieldworkPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [activeTab, setActiveTab] = useState('findings')

  const { data: obsData } = useQuery({
    queryKey: ['observations', id],
    queryFn: () => getObs(id),
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['observations', id] })

  const seedMutation = useMutation({
    mutationFn: () => seedObs(id),
    onSuccess: (data) => {
      if (data.seeded > 0) showToast(`${data.seeded} observations pre-populated from Process Understanding`)
      invalidate()
    },
  })

  const createMutation = useMutation({
    mutationFn: (obsType) => createObs(id, { obs_type: obsType, title: 'New observation' }),
    onSuccess: invalidate,
  })

  const patchMutation = useMutation({
    mutationFn: ({ obsId, payload }) => patchObs(id, obsId, payload),
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: (obsId) => deleteObs(id, obsId),
    onSuccess: invalidate,
  })

  const unlocked = obsData?.fieldwork_unlocked ?? false
  const activeTabMeta = TABS.find((t) => t.key === activeTab)
  const activeItems = obsData?.[activeTab] || []
  const total = obsData?.total ?? 0

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
      <button
        onClick={() => navigate(`/engagements/${id}/planning`)}
        className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
      >
        <ArrowLeft size={16} /> Back to planning
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-h1 text-fg">Fieldwork</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Record audit observations — findings, recommendations, good practices, and improvements.
          </p>
        </div>
        {unlocked && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}>
              <Sparkles size={14} /> Seed from planning
            </Button>
            <Button onClick={() => createMutation.mutate(activeTabMeta?.obsType || 'finding')}>
              <Plus size={14} /> Add observation
            </Button>
          </div>
        )}
      </div>

      {!unlocked && (
        <div className="mt-8 rounded-xl border border-sev-med/25 bg-sev-med/10 p-6 text-center">
          <Lock size={28} className="mx-auto mb-2 text-sev-med" />
          <p className="text-sm font-medium text-sev-med">Fieldwork is locked</p>
          <p className="mt-1 text-xs text-sev-med">
            Sign off the Work Program to unlock fieldwork recording.
          </p>
          <button
            onClick={() => navigate(`/engagements/${id}/planning/work-program`)}
            className="mt-3 text-xs text-brand underline"
          >
            Open Work Program →
          </button>
        </div>
      )}

      {unlocked && (
        <>
          {/* Tabs */}
          <div className="mt-6 flex border-b border-line">
            {TABS.map((tab) => {
              const count = obsData?.[tab.key]?.length ?? 0
              const Icon = tab.icon
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 border-b-2 px-4 pb-2.5 pt-1 text-sm font-medium transition-colors ${
                    activeTab === tab.key
                      ? 'border-brand text-brand'
                      : 'border-transparent text-fg-subtle hover:text-fg'
                  }`}
                >
                  <Icon size={14} className={activeTab === tab.key ? 'text-brand' : tab.color} />
                  {tab.label}
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                    count > 0 ? 'bg-brand-subtle text-brand' : 'bg-surface-3 text-fg-subtle'
                  }`}>{count}</span>
                </button>
              )
            })}
          </div>

          {activeItems.length === 0 ? (
            <div className="border border-line mt-8 rounded-xl bg-surface p-8 text-center">
              {activeTabMeta && <activeTabMeta.icon size={28} className={`mx-auto mb-2 ${activeTabMeta.color} opacity-40`} />}
              <p className="text-sm text-fg-subtle">
                No {activeTabMeta?.label.toLowerCase() || 'observations'} yet.
                {activeTab === 'findings' && ' Click "Seed from planning" to pre-populate from Process Understanding.'}
              </p>
              <button
                onClick={() => createMutation.mutate(activeTabMeta?.obsType || 'finding')}
                className="mt-3 flex items-center gap-1 mx-auto text-xs text-brand hover:underline"
              >
                <Plus size={12} /> Add manually
              </button>
            </div>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
              <table className="w-full min-w-[900px]">
                <thead>
                  <tr className="border-b border-line bg-surface-3 text-left">
                    {['Title / Source', 'Criteria', 'Detailed observation', 'Root cause', 'Risk', ''].map((h) => (
                      <th key={h} className="px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeItems.map((obs) => (
                    <ObsRow
                      key={obs.id}
                      obs={obs}
                      engagementId={id}
                      onPatch={(obsId, payload) => patchMutation.mutate({ obsId, payload })}
                      onDelete={(obsId) => deleteMutation.mutate(obsId)}
                    />
                  ))}
                </tbody>
              </table>
              <div className="flex justify-end px-4 py-2">
                <button
                  onClick={() => createMutation.mutate(activeTabMeta?.obsType || 'finding')}
                  className="flex items-center gap-1 text-xs text-brand hover:underline"
                >
                  <Plus size={12} /> Add row
                </button>
              </div>
            </div>
          )}

          {total > 0 && (
            <p className="mt-3 text-center text-xs text-fg-subtle">
              Click any cell to edit. Changes save automatically.
            </p>
          )}

          {/* AI fieldwork agents */}
          <div className="mt-10">
            <SectionHeading>AI fieldwork agents</SectionHeading>
            <p className="mt-1 text-sm text-fg-muted">Agents that do the fieldwork and write their results into the matrix. Each proposal is yours to accept or dismiss.</p>
            <div className="mt-4 grid grid-cols-1 gap-4">
              <GovernanceAssessorPanel engagementId={id} />
              <DataAnalysisPanel engagementId={id} />
              <PrivacyGuardPanel engagementId={id} />
              <VendorGuardPanel engagementId={id} />
              <EvidenceChasePanel engagementId={id} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
