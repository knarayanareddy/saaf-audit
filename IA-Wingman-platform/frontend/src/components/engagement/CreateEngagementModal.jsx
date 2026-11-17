import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { createEngagement, suggestSummary } from '../../api/engagements'
import { suggestName } from '../../api/ai'
import { useStore } from '../../store/useStore'
import { ENTITY_ORDER, ENTITIES, AUDIT_TYPES } from '../../lib/entities'

const TYPES = Object.keys(AUDIT_TYPES)

const empty = {
  audit_code: '', name: '', entity: 'GRP', audit_type: 'compliance',
  summary: '', planning_date: '', start_date: '', end_date: '',
  draft_report_date: '', final_report_date: '', scope_period: '',
  lead_auditor: '', team_members: '',
}

export default function CreateEngagementModal({ open, onClose }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [form, setForm] = useState(empty)
  const [suggesting, setSuggesting] = useState(false)
  const [suggestingName, setSuggestingName] = useState(false)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const doSuggestName = async () => {
    setSuggestingName(true)
    try {
      const { name } = await suggestName({ entity: form.entity, audit_type: form.audit_type, hint: form.name || null })
      set('name', name)
    } catch {
      showToast('AI suggestion failed', 'error')
    }
    setSuggestingName(false)
  }

  const mutation = useMutation({
    mutationFn: () =>
      createEngagement({
        ...form,
        status: 'in_planning',
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
      showToast('Engagement created')
      setForm(empty)
      onClose()
    },
    onError: () => showToast('Could not create engagement', 'error'),
  })

  const doSuggest = async () => {
    if (!form.name) return
    setSuggesting(true)
    try {
      const { summary } = await suggestSummary({ name: form.name, entity: form.entity, audit_type: form.audit_type })
      set('summary', summary)
    } catch {
      showToast('AI suggestion failed', 'error')
    }
    setSuggesting(false)
  }

  const label = 'mb-1 block text-caption text-fg-subtle'
  const field = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20'

  return (
    <Modal open={open} onClose={onClose} title="New Engagement">
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={label}>Audit code</label>
            <input className={field} placeholder="26-001" value={form.audit_code} onChange={(e) => set('audit_code', e.target.value)} />
          </div>
          <div className="col-span-2">
            <div className="flex items-center justify-between">
              <label className={label}>Audit name *</label>
              <button onClick={doSuggestName} disabled={suggestingName} className="mb-1 flex items-center gap-1 text-xs text-brand hover:underline disabled:opacity-40">
                <Sparkles size={12} /> {suggestingName ? 'Thinking…' : 'AI suggest'}
              </button>
            </div>
            <input className={field} value={form.name} onChange={(e) => set('name', e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
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
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className={label}>Summary (optional)</label>
            <button onClick={doSuggest} disabled={!form.name || suggesting} className="mb-1 flex items-center gap-1 text-xs text-brand hover:underline disabled:opacity-40">
              <Sparkles size={12} /> {suggesting ? 'Thinking…' : 'AI suggest'}
            </button>
          </div>
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

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={!form.name || mutation.isPending}>
            {mutation.isPending ? 'Creating…' : 'Create engagement'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
