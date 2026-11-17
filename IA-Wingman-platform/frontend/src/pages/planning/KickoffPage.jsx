import { useParams, useNavigate } from 'react-router-dom'
import { downloadFile } from '../../api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Users, Sparkles, Loader2, Download } from 'lucide-react'
import client from '../../api/client'
import EditableText from '../../components/ui/EditableText'
import Button from '../../components/ui/Button'
import ScopeContributionPanel from '../../components/planning/ScopeContributionPanel'
import { kickoffGenerateScope, kickoffGetScope, kickoffPublishScope } from '../../api/planning'
import { useStore } from '../../store/useStore'

const getKickoff = (id) => client.get(`/planning/${id}/kickoff`).then((r) => r.data)
const updateKickoff = (id, p) => client.patch(`/planning/${id}/kickoff`, p).then((r) => r.data)
const draftKickoff = (id) => client.post(`/planning/${id}/kickoff/draft`).then((r) => r.data)

const SECTIONS = [
  { key: 'notes_welcome', label: '1. Welcome & objectives', hint: 'Opening, confirm attendees, state purpose' },
  { key: 'notes_context', label: '2. Audit information & context', hint: 'Why in 2026 plan, objective, hours budgeted' },
  { key: 'notes_documentation', label: '3. Available documentation', hint: 'Previous audits, risk assessments, control reports available' },
  { key: 'notes_missing', label: '4. Missing documentation', hint: 'What still needs to be provided by auditee' },
  { key: 'notes_scope', label: '5. Scope — subjects, fraud risk, ESG, budget', hint: 'Scope items, fraud triangle, ESG link, confirm hours fit' },
  { key: 'notes_risks', label: '6. Risk assessment approach', hint: 'Inherent risk, control risk, detection risk' },
  { key: 'notes_team', label: '7. Team composition & planning', hint: 'Roles, independence, availability, milestone dates' },
  { key: 'notes_other', label: '8. Other aspects', hint: 'Data analytics, IT tools, confidentiality, access restrictions' },
  { key: 'notes_aob', label: '9. Any other business', hint: 'Open questions for auditee' },
  { key: 'notes_next_steps', label: '10. Next steps', hint: 'Actions, owners, next meeting date' },
]

export default function KickoffPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['kickoff', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  const { data: agenda } = useQuery({
    queryKey: ['kickoff', id],
    queryFn: () => getKickoff(id),
    refetchInterval: (q) => (q.state.data?.status === 'drafting' ? 3000 : false),
  })

  const draft = useMutation({
    mutationFn: () => draftKickoff(id),
    onSuccess: () => { showToast('Drafting kick-off notes…'); invalidate() },
  })
  const patch = useMutation({ mutationFn: (p) => updateKickoff(id, p), onSuccess: invalidate })

  const downloadWord = async () => {
    try {
      await downloadFile(`/planning/${id}/kickoff/export-word`, 'KickOff-agenda.docx')
    } catch {
      showToast('Export failed', 'error')
    }
  }

  const status = agenda?.status || 'not_started'

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-8">
      <button onClick={() => navigate(`/engagements/${id}/planning`)} className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand">
        <ArrowLeft size={16}/> Back to planning
      </button>

      <div className="flex items-center justify-between">
        <h1 className="text-h1 text-fg">Kick-off Meeting Agenda</h1>
        <div className="flex gap-2">
          <Button onClick={() => draft.mutate()} disabled={draft.isPending} variant={status === 'draft_ready' ? 'secondary' : 'primary'}>
            <Sparkles size={14}/> {status === 'draft_ready' ? 'Re-draft' : 'Draft with AI'}
          </Button>
          {status === 'draft_ready' && (
            <Button variant="ghost" onClick={downloadWord}>
              <Download size={14}/> Download Word
            </Button>
          )}
        </div>
      </div>
      <p className="mt-1 text-sm text-fg-muted">
        Prepare notes for each agenda item before the kick-off meeting. All sections are editable.
      </p>

      {status === 'drafting' && (
        <div className="border border-line mt-6 flex items-center gap-3 rounded-xl bg-surface p-5 text-sm text-fg-muted">
          <Loader2 size={20} className="animate-spin text-brand"/> Generating kick-off notes from your planning data…
        </div>
      )}

      {status === 'not_started' && (
        <div className="border border-line mt-6 rounded-xl bg-surface p-6 text-center">
          <Users size={28} className="mx-auto text-brand-light mb-2"/>
          <p className="text-sm text-fg-muted">Click "Draft with AI" to generate prepared notes for each agenda item based on your Topic Intelligence memo and scope.</p>
        </div>
      )}

      {status === 'draft_ready' && (
        <>
          <div className="mt-4 rounded-xl border border-brand/20 bg-brand-subtle/30 p-4">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-fg-muted">Purpose of this audit</label>
            <EditableText
              value={agenda.audit_purpose || ''}
              onSave={(v) => patch.mutate({ audit_purpose: v })}
              placeholder="Why this audit — what it is for and aims to achieve."
              readable
            />
          </div>

          {(agenda.questions_for_auditor?.length > 0) && (
            <div className="border border-line mt-3 rounded-xl bg-surface p-4">
              <span className="text-sm font-semibold text-fg">Questions to ask the auditor</span>
              <ul className="mt-2 space-y-1.5">
                {agenda.questions_for_auditor.map((q, i) => (
                  <li key={i} className="flex gap-2 text-sm text-fg">
                    <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-brand" />
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-fg-muted">Meeting date</label>
              <EditableText value={agenda.meeting_date || ''} onSave={(v) => patch.mutate({ meeting_date: v })} placeholder="DD/MM/YYYY" multiline={false}/>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-fg-muted">Attendees</label>
              <EditableText value={agenda.attendees || ''} onSave={(v) => patch.mutate({ attendees: v })} placeholder="IA team + auditee contacts" multiline={false}/>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {SECTIONS.map(({ key, label, hint }) => (
              <div key={key} className="border border-line rounded-xl bg-surface p-4">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm font-semibold text-fg">{label}</span>
                  <span className="text-xs text-fg-subtle">{hint}</span>
                </div>
                <EditableText
                  value={agenda[key] || ''}
                  onSave={(v) => patch.mutate({ [key]: v })}
                  placeholder="Click to add notes…"
                  readable
                />
              </div>
            ))}
          </div>

          <ScopeContributionPanel
            engagementId={id}
            generateFn={() => kickoffGenerateScope(id)}
            getStoredFn={() => kickoffGetScope(id)}
            publishFn={(payload) => kickoffPublishScope(id, payload)}
            queryKey="kickoff-scope"
          />
        </>
      )}
    </div>
  )
}
