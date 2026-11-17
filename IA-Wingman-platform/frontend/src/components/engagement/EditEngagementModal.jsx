import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { updateEngagement } from '../../api/engagements'
import { useStore } from '../../store/useStore'
import { ENTITY_ORDER, ENTITIES, AUDIT_TYPES } from '../../lib/entities'
import JurisdictionSelect from '../planning/JurisdictionSelect'

const TYPES = Object.keys(AUDIT_TYPES)
const STATUSES = ['to_be_scheduled', 'in_planning', 'in_fieldwork', 'in_reporting', 'closed']

export default function EditEngagementModal({ open, onClose, engagement }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [form, setForm] = useState({})

  useEffect(() => {
    if (engagement) {
      setForm({
        audit_code: engagement.audit_code || '',
        name: engagement.name || '',
        entity: engagement.entity || 'GRP',
        audit_type: engagement.audit_type || 'compliance',
        status: engagement.status || 'to_be_scheduled',
        summary: engagement.summary || '',
        planning_date: engagement.planning_date || '',
        start_date: engagement.start_date || '',
        end_date: engagement.end_date || '',
        draft_report_date: engagement.draft_report_date || '',
        final_report_date: engagement.final_report_date || '',
        scope_period: engagement.scope_period || '',
        lead_auditor: engagement.lead_auditor || '',
        team_members: Array.isArray(engagement.team_members) ? engagement.team_members.join(', ') : '',
      })
    }
  }, [engagement])

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const mutation = useMutation({
    mutationFn: () =>
      updateEngagement(engagement.id, {
        ...form,
        team_members: form.team_members
          ? form.team_members.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
        audit_code: form.audit_code || null,
        summary: form.summary || null,
        lead_auditor: form.lead_auditor || null,
        planning_date: form.planning_date || null,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        draft_report_date: form.draft_report_date || null,
        final_report_date: form.final_report_date || null,
        scope_period: form.scope_period || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['engagements'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
      qc.invalidateQueries({ queryKey: ['engagement', engagement.id] })
      showToast('Engagement updated')
      onClose()
    },
    onError: () => showToast('Could not update engagement', 'error'),
  })

  const label = 'mb-1 block text-caption text-fg-subtle'
  const field = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20'

  if (!engagement) return null

  return (
    <Modal open={open} onClose={onClose} title="Edit Engagement">
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label}>Audit code</label>
            <input className={field} placeholder="26-001" value={form.audit_code} onChange={(e) => set('audit_code', e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={label}>Audit name *</label>
            <input className={field} value={form.name} onChange={(e) => set('name', e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label}>Entity *</label>
            <select className={field} value={form.entity} onChange={(e) => set('entity', e.target.value)}>
              {ENTITY_ORDER.map((code) => <option key={code} value={code}>{ENTITIES[code].label}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Audit type *</label>
            <select className={field} value={form.audit_type} onChange={(e) => set('audit_type', e.target.value)}>
              {TYPES.map((t) => <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Status</label>
            <select className={field} value={form.status} onChange={(e) => set('status', e.target.value)}>
              {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className={label}>Summary (optional)</label>
          <textarea className={field} rows={2} value={form.summary} onChange={(e) => set('summary', e.target.value)} />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label}>Planning Date</label>
            <input type="date" className={field} value={form.planning_date} onChange={(e) => set('planning_date', e.target.value)} />
          </div>
          <div>
            <label className={label}>Fieldwork Start Date</label>
            <input type="date" className={field} value={form.start_date} onChange={(e) => set('start_date', e.target.value)} />
          </div>
          <div>
            <label className={label}>Fieldwork End Date</label>
            <input type="date" className={field} value={form.end_date} onChange={(e) => set('end_date', e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label}>Draft Report Date</label>
            <input type="date" className={field} value={form.draft_report_date} onChange={(e) => set('draft_report_date', e.target.value)} />
          </div>
          <div>
            <label className={label}>Final Report Date</label>
            <input type="date" className={field} value={form.final_report_date} onChange={(e) => set('final_report_date', e.target.value)} />
          </div>
          <div>
            <label className={label}>Scope period</label>
            <input className={field} placeholder="Jan – Dec 2025" value={form.scope_period} onChange={(e) => set('scope_period', e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={label}>Lead auditor</label>
            <input className={field} placeholder="AB" value={form.lead_auditor} onChange={(e) => set('lead_auditor', e.target.value)} />
            <p className="mt-1 text-[11px] text-fg-subtle">Free text — your initials</p>
          </div>
          <div>
            <label className={label}>Team members</label>
            <input className={field} placeholder="AB, CD, EF" value={form.team_members} onChange={(e) => set('team_members', e.target.value)} />
            <p className="mt-1 text-[11px] text-fg-subtle">Comma-separated</p>
          </div>
        </div>

        <div>
          <label className={label}>Countries in scope</label>
          <JurisdictionSelect engagementId={engagement.id} compact />
          <p className="mt-1 text-[11px] text-fg-subtle">Saved immediately. Drives Topic Intelligence and Laws &amp; Regulations.</p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={!form.name || mutation.isPending}>
            {mutation.isPending ? 'Saving…' : 'Save changes'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
