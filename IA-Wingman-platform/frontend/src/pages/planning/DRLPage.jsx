import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { downloadFile } from '../../api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Sparkles, Loader2, Download, FileSearch, Mail, BellRing, FileCheck,
  AlertTriangle, Check, ClipboardList,
} from 'lucide-react'
import client from '../../api/client'
import { listDocuments } from '../../api/agents'
import Button from '../../components/ui/Button'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import { useStore } from '../../store/useStore'

const getDRL = (id) => client.get(`/planning/${id}/drl`).then((r) => r.data)
const generateDRL = (id) => client.post(`/planning/${id}/drl/generate`).then((r) => r.data)
const patchDRLItem = (id, itemId, payload) =>
  client.patch(`/planning/${id}/drl/items/${itemId}`, payload).then((r) => r.data)
const getDashboard = (id) => client.get(`/planning/${id}/drl/dashboard`).then((r) => r.data)
const getCoverage = (id) => client.get(`/planning/${id}/drl/coverage`).then((r) => r.data)
const draftEmail = (id, contact) =>
  client.post(`/planning/${id}/drl/distribution-email`, { contact }).then((r) => r.data)
const draftReminders = (id, contact) =>
  client.post(`/planning/${id}/drl/reminders`, { contact }).then((r) => r.data)
const validateItem = (id, itemId, documentId) =>
  client.post(`/planning/${id}/drl/items/${itemId}/validate`, { document_id: documentId }).then((r) => r.data)

const STATUS_OPTIONS = [
  { value: 'not_requested', label: 'Not requested', color: 'bg-surface-3 text-fg-muted' },
  { value: 'requested', label: 'Requested', color: 'bg-sev-med/10 text-sev-med' },
  { value: 'received', label: 'Received', color: 'bg-sev-low/10 text-sev-low' },
  { value: 'not_needed', label: 'Not needed', color: 'bg-sev-high/10 text-sev-high' },
]

const CATEGORY_OPTIONS = ['Policy', 'Procedure', 'Report', 'Data', 'Evidence', 'Contract']

const CONCLUSION_STYLE = {
  sufficient: 'bg-sev-low/10 text-sev-low',
  'partially sufficient': 'bg-sev-med/10 text-sev-med',
  insufficient: 'bg-sev-high/10 text-sev-high',
}

// An always-editable cell: looks like text, reveals a border on hover/focus, and
// saves on blur or Enter (Esc reverts). Every DRL cell is the auditor's to change.
function CellInput({ value, onSave, multiline = false, type = 'text', className = '' }) {
  const [v, setV] = useState(value ?? '')
  useEffect(() => { setV(value ?? '') }, [value])
  const commit = () => { if ((v ?? '') !== (value ?? '')) onSave(v) }
  const cls = `w-full resize-none rounded border border-transparent bg-transparent px-2 py-1 text-sm text-fg outline-none transition hover:border-line focus:border-brand focus:bg-surface focus:ring-1 focus:ring-brand/20 ${className}`
  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !multiline) { e.preventDefault(); e.currentTarget.blur() }
    if (e.key === 'Escape') { setV(value ?? ''); e.currentTarget.blur() }
  }
  if (multiline) {
    return <textarea rows={2} value={v} onChange={(e) => setV(e.target.value)} onBlur={commit} onKeyDown={onKeyDown} className={cls} />
  }
  return <input type={type} value={v} onChange={(e) => setV(e.target.value)} onBlur={commit} onKeyDown={onKeyDown} className={cls} />
}

// What the request settles, as the generator recorded it while merging. A
// request covering nothing is not necessarily wrong — standard-practice items
// exist — but it is the one an auditor should be able to see and question.
function CoversTag({ refs }) {
  const count = (refs || []).length
  if (count) {
    return (
      <span className="ml-2 mt-1 inline-flex items-center gap-1 rounded-full bg-sev-low/10 px-2 py-0.5 text-[10px] font-medium text-sev-low"
        title={`Settles ${refs.join(', ')}`}>
        covers {count}
      </span>
    )
  }
  return (
    <span className="ml-2 mt-1 inline-flex items-center gap-1 rounded-full bg-surface-3 px-2 py-0.5 text-[10px] font-medium text-fg-subtle"
      title="No test in the work program asks for this">
      no test
    </span>
  )
}

function DRLRow({ item, onPatch, overdue }) {
  const statusOpt = STATUS_OPTIONS.find((o) => o.value === item.status) || STATUS_OPTIONS[0]
  const validation = item.validation

  return (
    <tr className="border-b border-line align-top hover:bg-surface-3/40">
      <td className="px-2 py-2 min-w-[180px]">
        <CellInput value={item.document} onSave={(v) => onPatch(item.id, { document: v })} className="font-medium" />
        <select
          value={CATEGORY_OPTIONS.includes(item.category) ? item.category : ''}
          onChange={(e) => onPatch(item.id, { category: e.target.value })}
          className="mt-1 ml-2 rounded border border-transparent bg-transparent px-1 py-0.5 text-[10px] font-semibold uppercase text-fg-subtle outline-none transition hover:border-line focus:border-brand"
        >
          <option value="" disabled>Category…</option>
          {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {validation && (
          <span className={`ml-2 mt-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${CONCLUSION_STYLE[validation.conclusion] || 'bg-surface-3 text-fg-muted'}`}>
            <FileCheck size={10} /> {validation.conclusion}
          </span>
        )}
        <CoversTag refs={item.covers} />
      </td>
      <td className="px-2 py-2 max-w-[260px] text-fg-muted">
        <CellInput value={item.description} onSave={(v) => onPatch(item.id, { description: v })} multiline className="text-xs" />
      </td>
      <td className="px-2 py-2 max-w-[160px] text-fg-muted">
        <CellInput value={item.regulatory_basis} onSave={(v) => onPatch(item.id, { regulatory_basis: v })} className="text-xs" />
      </td>
      <td className="px-2 py-2 min-w-[120px]">
        <CellInput value={item.requested_from} onSave={(v) => onPatch(item.id, { requested_from: v })} className="text-xs font-medium" />
      </td>
      <td className="px-2 py-2 min-w-[130px]">
        <CellInput value={item.deadline} onSave={(v) => onPatch(item.id, { deadline: v })} type="date" className="text-xs" />
        {overdue && (
          <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-sev-high/10 px-2 py-0.5 text-[10px] font-medium text-sev-high">
            <AlertTriangle size={10} /> overdue
          </span>
        )}
      </td>
      <td className="px-2 py-2">
        <select
          value={item.status}
          onChange={(e) => onPatch(item.id, { status: e.target.value })}
          className={`rounded border-0 px-2 py-1 text-[11px] font-medium outline-none focus:ring-1 focus:ring-brand ${statusOpt.color}`}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </td>
    </tr>
  )
}

function StatTile({ label, value, tone = 'fg' }) {
  const toneCls = {
    fg: 'text-fg', brand: 'text-brand',
    amber: 'text-sev-med', red: 'text-sev-high',
    emerald: 'text-sev-low',
  }[tone]
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3">
      <div className={`text-2xl font-semibold ${toneCls}`}>{value}</div>
      <div className="mt-0.5 text-caption text-fg-subtle">{label}</div>
    </div>
  )
}

export default function DRLPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const [contact, setContact] = useState({ name: '', email: '', organization: '' })
  const [emailOpen, setEmailOpen] = useState(false)
  const [remindOpen, setRemindOpen] = useState(false)
  const [valItem, setValItem] = useState('')
  const [valDoc, setValDoc] = useState('')
  const [valOpen, setValOpen] = useState(false)

  const { data: drl } = useQuery({ queryKey: ['drl', id], queryFn: () => getDRL(id) })
  const { data: coverage } = useQuery({
    queryKey: ['drl-coverage', id],
    queryFn: () => getCoverage(id),
  })

  const { data: dashboard } = useQuery({
    queryKey: ['drl-dashboard', id],
    queryFn: () => getDashboard(id),
    enabled: !!drl?.items?.length,
  })
  const { data: documents } = useQuery({ queryKey: ['documents', id], queryFn: () => listDocuments(id) })

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ['drl', id] })
    qc.invalidateQueries({ queryKey: ['drl-dashboard', id] })
    // Generating rewrites which needs each request settles, so the cover
    // figures change at exactly this moment. Left out, the strip kept showing
    // the previous run's numbers until someone reloaded the page — the one
    // number the screen is here for, stale when it matters.
    qc.invalidateQueries({ queryKey: ['drl-coverage', id] })
  }

  const generateMutation = useMutation({
    mutationFn: () => generateDRL(id),
    onSuccess: (data) => { qc.setQueryData(['drl', id], data); invalidateAll(); showToast('DRL generated') },
    onError: (e) => showToast(e.response?.data?.detail || 'Generation failed — check Anthropic API key', 'error'),
  })

  const patchMutation = useMutation({
    mutationFn: ({ itemId, payload }) => patchDRLItem(id, itemId, payload),
    // A patch can change `status` to received, which the dashboard counts.
    // It cannot change `covers`, so the cover figures are left alone.
    onSuccess: (data) => { qc.setQueryData(['drl', id], (prev) => ({ ...prev, items: data.items })); qc.invalidateQueries({ queryKey: ['drl-dashboard', id] }) },
  })

  const emailMutation = useMutation({
    mutationFn: () => draftEmail(id, contact),
    onSuccess: () => { setEmailOpen(false); invalidateAll(); showToast('Distribution email drafted (not sent)') },
    onError: (e) => showToast(e.response?.data?.detail || 'Draft failed', 'error'),
  })
  const reminderMutation = useMutation({
    mutationFn: () => draftReminders(id, contact),
    onSuccess: () => { setRemindOpen(false); invalidateAll(); showToast('Reminders drafted (not sent)') },
    onError: (e) => showToast(e.response?.data?.detail || 'Draft failed', 'error'),
  })
  const validateMutation = useMutation({
    mutationFn: () => validateItem(id, valItem, valDoc),
    onSuccess: () => { setValOpen(false); invalidateAll(); showToast('Document validated') },
    onError: (e) => showToast(e.response?.data?.detail || 'Validation failed', 'error'),
  })

  const downloadWord = async () => {
    try { await downloadFile(`/planning/${id}/drl/export-word`, 'DRL.docx') }
    catch { showToast('Export failed', 'error') }
  }

  const items = drl?.items || []
  const overdueIds = useMemo(
    () => new Set((dashboard?.overdue || []).map((r) => r.id)),
    [dashboard],
  )
  const email = drl?.distribution_email
  const reminders = drl?.reminder_log
  const readyDocs = (documents || []).filter((d) => d.upload_status === 'ready')

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
          <h1 className="text-h1 text-fg">Document Request List</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Documents to request from the auditee (PBC) — generated from your accepted frameworks and scope.
            Every cell is editable, including deadlines. The PBC assistant below tracks status and drafts
            requests, reminders and document checks.
          </p>
        </div>
        <div className="flex gap-2">
          {items.length > 0 && (
            <Button variant="ghost" onClick={downloadWord}>
              <Download size={14} /> Download Word
            </Button>
          )}
          <Button
            variant={items.length > 0 ? 'secondary' : 'primary'}
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending
              ? <><Loader2 size={14} className="animate-spin" /> Generating…</>
              : <><Sparkles size={14} /> {items.length > 0 ? 'Regenerate' : 'Generate DRL'}</>}
          </Button>
        </div>
      </div>

      {/* PBC status dashboard — deterministic, free */}
      {items.length > 0 && dashboard && (
        <div className="mt-6">
          <div className="flex items-center gap-2 text-sm font-semibold text-fg">
            <ClipboardList size={16} className="text-brand" /> PBC status
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic</span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatTile label="Documents" value={dashboard.total_items} />
            <StatTile label="Received" value={dashboard.received_count} tone="emerald" />
            <StatTile label="Outstanding" value={dashboard.outstanding_count} tone="amber" />
            <StatTile label="Overdue" value={dashboard.overdue_count} tone={dashboard.overdue_count ? 'red' : 'fg'} />
            <StatTile label="Completion" value={`${dashboard.completion_pct}%`} tone="brand" />
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-3">
            <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${dashboard.completion_pct}%` }} />
          </div>
          {dashboard.overdue_count > 0 && (
            <div className="mt-2 text-caption text-fg-muted">
              Overdue: {dashboard.overdue.map((r) => `${r.document || r.id} (${r.days_overdue}d)`).join(' · ')}
            </div>
          )}
        </div>
      )}

      {/* Does the list cover the testing? Counted by reference, not by keyword. */}
      {coverage && (coverage.needs > 0 || items.length > 0) && (
        <div className="mt-6">
          <div className="flex items-center gap-2 text-sm font-semibold text-fg">
            <ClipboardList size={16} className="text-brand" /> Cover of the work program
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic</span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Evidence the tests need" value={coverage.requestable} />
            <StatTile label="Nobody asked for" value={coverage.unrequested}
              tone={coverage.unrequested ? 'red' : 'emerald'} />
            <StatTile label="Requests serving no test" value={coverage.unused_requests}
              tone={coverage.unused_requests ? 'amber' : 'emerald'} />
            <StatTile label="Controls declaring nothing" value={coverage.controls_without_needs}
              tone={coverage.controls_without_needs ? 'amber' : 'emerald'} />
          </div>
          {coverage.unrequested > 0 && (
            <div className="mt-2 text-caption text-fg-muted">
              Not requested: {coverage.detail?.unrequested?.slice(0, 4).map((n) => n.title).join(' · ')}
              {coverage.unrequested > 4 && ` · +${coverage.unrequested - 4} more`}
            </div>
          )}
          {coverage.needs === 0 && (
            <p className="mt-2 text-caption text-fg-subtle">
              No test has said what evidence it needs yet, so every request here counts as
              serving none.{' '}
              {coverage.work_program_signed
                ? 'This work program is signed, so it cannot be regenerated — record what a test needs on the matrix instead.'
                : 'Regenerate the work program to fill that in.'}
            </p>
          )}
        </div>
      )}

      {!generateMutation.isPending && items.length === 0 && (
        <div className="border border-line mt-10 rounded-xl bg-surface p-10 text-center">
          <FileSearch size={36} className="mx-auto mb-3 text-brand-light" />
          <p className="text-sm text-fg-muted">
            Click "Generate DRL" to create a document request list from your accepted frameworks,
            scope items, and control requirements. Each document includes the regulatory basis
            and which department to request it from.
          </p>
        </div>
      )}

      {generateMutation.isPending && (
        <div className="border border-line mt-8 flex items-center gap-3 rounded-xl bg-surface p-6 text-sm text-fg-muted">
          <Loader2 size={20} className="animate-spin text-brand" />
          Generating document request list from your planning data…
        </div>
      )}

      {items.length > 0 && (
        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line bg-surface-3 text-left">
                {['Document', 'Description', 'Regulatory basis', 'Requested from', 'Deadline', 'Status'].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <DRLRow
                  key={item.id}
                  item={item}
                  overdue={overdueIds.has(item.id)}
                  onPatch={(itemId, payload) => patchMutation.mutate({ itemId, payload })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PBC assistant — opt-in AI (drafts only, never sent) */}
      {items.length > 0 && (
        <div className="mt-8 rounded-xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-fg">
            <Mail size={16} className="text-brand" /> PBC assistant
            <span className="rounded-full bg-brand-subtle px-1.5 py-0.5 text-[11px] font-medium text-brand">AI · opt-in</span>
          </div>
          <p className="mt-1 text-sm text-fg-muted">
            Drafts a distribution email and reminders, and checks received documents against a request.
            Everything is drafted for your review — nothing is sent.
          </p>

          {/* Optional auditee contact */}
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <input value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })}
              placeholder="Contact name (optional)"
              className="rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg placeholder:text-fg-subtle" />
            <input value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })}
              placeholder="Contact email (optional)"
              className="rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg placeholder:text-fg-subtle" />
            <input value={contact.organization} onChange={(e) => setContact({ ...contact, organization: e.target.value })}
              placeholder="Organisation (optional)"
              className="rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg placeholder:text-fg-subtle" />
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setEmailOpen(true)} disabled={emailMutation.isPending}>
              {emailMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />} Draft distribution email
            </Button>
            <Button variant="secondary" onClick={() => setRemindOpen(true)} disabled={reminderMutation.isPending}>
              {reminderMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <BellRing size={14} />} Draft reminders
            </Button>
          </div>

          {/* Distribution email result */}
          {email && (
            <div className="mt-4 rounded-lg border border-line bg-surface-2 p-4">
              <div className="text-caption font-semibold uppercase tracking-wide text-fg-subtle">Distribution email · modelled, not sent</div>
              <div className="mt-1 text-sm font-medium text-fg">{email.subject}</div>
              <pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-fg-muted">{email.body}</pre>
            </div>
          )}

          {/* Reminders result */}
          {reminders && (reminders.messages?.length > 0) && (
            <div className="mt-4 space-y-2">
              <div className="text-caption font-semibold uppercase tracking-wide text-fg-subtle">Reminders · modelled, not sent</div>
              {reminders.messages.map((m, i) => (
                <div key={i} className="rounded-lg border border-line bg-surface-2 p-3">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${m.escalated ? 'bg-sev-high/10 text-sev-high' : 'bg-sev-med/10 text-sev-med'}`}>
                      {m.escalated ? 'ESCALATED' : 'REMINDER'} · {m.days_overdue}d
                    </span>
                    <span className="text-sm font-medium text-fg">{m.subject}</span>
                  </div>
                  <pre className="mt-1.5 whitespace-pre-wrap font-sans text-sm text-fg-muted">{m.body}</pre>
                </div>
              ))}
            </div>
          )}
          {reminders && reminders.messages?.length === 0 && (
            <div className="mt-3 text-caption text-fg-subtle">{reminders.activity_log}</div>
          )}

          {/* Document validation */}
          <div className="mt-5 border-t border-line pt-4">
            <div className="flex items-center gap-2 text-sm font-medium text-fg">
              <FileCheck size={15} className="text-brand" /> Validate a received document
            </div>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_auto]">
              <select value={valItem} onChange={(e) => setValItem(e.target.value)}
                className="rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg">
                <option value="">Select PBC item…</option>
                {items.map((it) => <option key={it.id} value={it.id}>{it.document}</option>)}
              </select>
              <select value={valDoc} onChange={(e) => setValDoc(e.target.value)}
                className="rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg">
                <option value="">Select uploaded document…</option>
                {readyDocs.map((d) => <option key={d.id} value={d.id}>{d.original_filename}</option>)}
              </select>
              <Button variant="secondary" onClick={() => setValOpen(true)}
                disabled={!valItem || !valDoc || validateMutation.isPending}>
                {validateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <FileCheck size={14} />} Validate
              </Button>
            </div>
            {readyDocs.length === 0 && (
              <p className="mt-1 text-caption text-fg-subtle">No uploaded documents yet — upload evidence on the Topic Intelligence / Process pages first.</p>
            )}
            {(() => {
              const v = items.find((it) => it.id === valItem)?.validation
              if (!v) return null
              return (
                <div className="mt-3 rounded-lg border border-line bg-surface-2 p-4">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${CONCLUSION_STYLE[v.conclusion] || 'bg-surface-3 text-fg-muted'}`}>
                    {v.conclusion === 'sufficient' ? <Check size={11} /> : <AlertTriangle size={11} />} {v.conclusion}
                  </span>
                  <span className="ml-2 text-caption text-fg-subtle">{v.filename}</span>
                  <p className="mt-2 text-sm text-fg-muted">{v.summary}</p>
                  {v.comments && <p className="mt-1 text-sm text-fg-muted">{v.comments}</p>}
                  {v.potential_issues?.length > 0 && (
                    <div className="mt-2 text-caption text-fg-muted"><span className="font-medium">Issues:</span> {v.potential_issues.join('; ')}</div>
                  )}
                  {v.missing_information?.length > 0 && (
                    <div className="mt-1 text-caption text-fg-muted"><span className="font-medium">Missing:</span> {v.missing_information.join('; ')}</div>
                  )}
                </div>
              )
            })()}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={emailOpen} onClose={() => setEmailOpen(false)} onConfirm={() => emailMutation.mutate()}
        title="Draft the distribution email?"
        description="Uses AI budget to draft a professional PBC request email to the auditee. The email is drafted for your review and is never sent."
        confirmLabel="Draft — uses AI" loading={emailMutation.isPending}
      />
      <ConfirmDialog
        open={remindOpen} onClose={() => setRemindOpen(false)} onConfirm={() => reminderMutation.mutate()}
        title="Draft reminders?"
        description="Uses AI budget to draft reminder messages for outstanding and overdue items. Drafted for your review; never sent."
        confirmLabel="Draft — uses AI" loading={reminderMutation.isPending}
      />
      <ConfirmDialog
        open={valOpen} onClose={() => setValOpen(false)} onConfirm={() => validateMutation.mutate()}
        title="Validate this document with AI?"
        description="Uses AI budget to judge whether the selected document satisfies the selected PBC request. The result is advisory."
        confirmLabel="Validate — uses AI" loading={validateMutation.isPending}
      />
    </div>
  )
}
