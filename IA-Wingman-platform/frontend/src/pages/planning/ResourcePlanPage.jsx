import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Users, Sparkles, Check, Loader2, Calendar, Clock } from 'lucide-react'
import { getResourcePlan, updateResourcePlan, generateTimeline } from '../../api/planning'
import Button from '../../components/ui/Button'
import { useStore } from '../../store/useStore'

const CHECKS = [
  { key: 'dates_confirmed', label: 'Dates confirmed', hint: 'Fieldwork start/end and report date set' },
  { key: 'hours_confirmed', label: 'Hours budget confirmed', hint: 'Total hours for this engagement agreed' },
  { key: 'team_confirmed', label: 'Team confirmed', hint: 'Lead auditor and team members assigned' },
  { key: 'head_ia_acknowledged', label: 'Head IA acknowledged', hint: 'Head IA aware of planning and timeline' },
]

function CheckItem({ check, value, onChange }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-lg border bg-surface px-4 py-3 hover:border-brand/30">
      <input
        type="checkbox"
        checked={!!value}
        onChange={(e) => onChange(check.key, e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-line-strong accent-brand"
      />
      <div>
        <div className="text-sm font-medium text-fg">{check.label}</div>
        <div className="text-xs text-fg-subtle">{check.hint}</div>
      </div>
      {value && <Check size={16} className="ml-auto mt-0.5 shrink-0 text-sev-low" />}
    </label>
  )
}

export default function ResourcePlanPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const { data: plan } = useQuery({
    queryKey: ['resource-plan', id],
    queryFn: () => getResourcePlan(id),
  })

  const [local, setLocal] = useState({})
  useEffect(() => { if (plan) setLocal(plan) }, [plan])

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['resource-plan', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  const patchMutation = useMutation({
    mutationFn: (payload) => updateResourcePlan(id, payload),
    onSuccess: (data) => { setLocal(data); invalidate() },
  })

  const timelineMutation = useMutation({
    mutationFn: () => generateTimeline(id),
    onSuccess: (data) => { setLocal(data); invalidate(); showToast('Timeline generated') },
    onError: () => showToast('Could not generate timeline', 'error'),
  })

  const save = (field, value) => {
    setLocal((prev) => ({ ...prev, [field]: value }))
    patchMutation.mutate({ [field]: value })
  }

  const completed = plan?.checks_completed ?? 0
  const progress = Math.round((completed / 4) * 100)

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
      <button
        onClick={() => navigate(`/engagements/${id}/planning`)}
        className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand"
      >
        <ArrowLeft size={16} /> Back to planning
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-h1 text-fg">Resource Planning</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Assign hours, milestones, and confirm the team before fieldwork starts.
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-brand">{progress}%</div>
          <div className="text-xs text-fg-subtle">{completed}/4 checks</div>
        </div>
      </div>

      {/* Dates */}
      <section className="border border-line mt-6 rounded-xl bg-surface p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-fg-muted">
          <Calendar size={14} /> Planning dates
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {[
            { key: 'planned_fieldwork_start', label: 'Fieldwork start' },
            { key: 'planned_fieldwork_end', label: 'Fieldwork end' },
            { key: 'planned_report_date', label: 'Report deadline' },
          ].map(({ key, label }) => (
            <div key={key}>
              <label className="mb-1 block text-xs font-medium text-fg-muted">{label}</label>
              <input
                type="date"
                value={local[key] || ''}
                onChange={(e) => save(key, e.target.value)}
                className="w-full rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-brand"
              />
            </div>
          ))}
        </div>
      </section>

      {/* Hours */}
      <section className="border border-line mt-4 rounded-xl bg-surface p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-fg-muted">
          <Clock size={14} /> Hours budget
        </h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-fg-muted">Total audit hours</label>
            <input
              type="number"
              min={0}
              max={2000}
              value={local.hours_budget || ''}
              onChange={(e) => save('hours_budget', parseInt(e.target.value) || null)}
              placeholder="e.g. 120"
              className="w-full rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-brand"
            />
          </div>
          <div className="pt-5">
            <Button
              variant="secondary"
              onClick={() => timelineMutation.mutate()}
              disabled={timelineMutation.isPending}
            >
              {timelineMutation.isPending
                ? <><Loader2 size={14} className="animate-spin" /> Generating…</>
                : <><Sparkles size={14} /> AI suggest</>}
            </Button>
          </div>
        </div>
        {local.ai_timeline && (
          <div className="mt-3 rounded-lg bg-brand-subtle/50 px-3 py-2.5 text-sm text-fg">
            <span className="mr-1 text-[10px] font-bold uppercase text-brand">AI suggestion</span>
            {local.ai_timeline}
          </div>
        )}
      </section>

      {/* Milestones */}
      {(local.milestones?.length > 0) && (
        <section className="border border-line mt-4 rounded-xl bg-surface p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-fg-muted">Milestones</h2>
          <div className="space-y-2">
            {(local.milestones || []).map((m, i) => (
              <div key={i} className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={!!m.done}
                  onChange={() => {
                    const updated = local.milestones.map((ms, j) =>
                      j === i ? { ...ms, done: !ms.done } : ms
                    )
                    save('milestones', updated)
                  }}
                  className="h-4 w-4 rounded border-line-strong accent-brand"
                />
                <span className={`flex-1 text-sm ${m.done ? 'line-through text-fg-subtle' : 'text-fg'}`}>{m.name}</span>
                <input
                  type="date"
                  value={m.date || ''}
                  onChange={(e) => {
                    const updated = local.milestones.map((ms, j) =>
                      j === i ? { ...ms, date: e.target.value } : ms
                    )
                    save('milestones', updated)
                  }}
                  className="rounded border border-line px-2 py-1 text-xs outline-none focus:border-brand"
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Confirmation checks */}
      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-fg-muted">Confirmation checklist</h2>
        <div className="space-y-2">
          {CHECKS.map((check) => (
            <CheckItem
              key={check.key}
              check={check}
              value={local.checks?.[check.key] ?? false}
              onChange={(key, value) => {
                setLocal((prev) => ({
                  ...prev,
                  checks: { ...(prev.checks || {}), [key]: value },
                }))
                patchMutation.mutate({ [key]: value })
              }}
            />
          ))}
        </div>
      </section>

      {completed === 4 && (
        <div className="mt-6 rounded-xl bg-sev-low/10 p-4 text-center text-sm font-medium text-sev-low">
          <Check size={16} className="mr-1 inline" />
          Resource planning complete — all 4 checks confirmed.
        </div>
      )}
    </div>
  )
}
