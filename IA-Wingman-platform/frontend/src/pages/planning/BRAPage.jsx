import { useParams, useNavigate } from 'react-router-dom'
import { downloadFile } from '../../api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, BarChart2, Sparkles, Loader2, Download, Check } from 'lucide-react'
import client from '../../api/client'
import EditableText from '../../components/ui/EditableText'
import Button from '../../components/ui/Button'
import ScopeContributionPanel from '../../components/planning/ScopeContributionPanel'
import { braGenerateScope, braGetScope, braPublishScope } from '../../api/planning'
import { useStore } from '../../store/useStore'

const getBRA = (id) => client.get(`/planning/${id}/bra`).then((r) => r.data)
const updateBRA = (id, p) => client.patch(`/planning/${id}/bra`, p).then((r) => r.data)
const draftBRA = (id) => client.post(`/planning/${id}/bra/draft`).then((r) => r.data)
const updateRiskItem = (id, ref, p) => client.patch(`/planning/${id}/bra/risk-items/${ref}`, p).then((r) => r.data)

const BG_SECTIONS = [
  { key: 'section_strategy', label: '1. Strategies, objectives and risks', hint: 'What does this area do? Key objectives, main risks, prior audit findings' },
  { key: 'section_risk_tolerance', label: '2. Risk tolerance', hint: 'Management\'s acceptable risk level for this activity' },
  { key: 'section_governance', label: '3. Governance & control processes', hint: 'Oversight, management reports, ICS/RCSA results, outstanding issues' },
  { key: 'section_frameworks', label: '4. Applicable frameworks & guidance', hint: 'Laws, regulations, internal policies, supervisory guidance' },
]

const RISK_LEVELS = ['High', 'Medium', 'Low']

function RiskRow({ item, onAccept, onUpdate }) {
  const color = item.inherent_risk === 'High' ? 'bg-sev-high/10 border-sev-high/25' : item.inherent_risk === 'Medium' ? 'bg-sev-med/10 border-sev-med/25' : 'bg-sev-low/10 border-sev-low/25'
  const residualColor = item.residual_risk === 'High' ? 'text-sev-high' : item.residual_risk === 'Medium' ? 'text-sev-med' : 'text-sev-low'

  return (
    <div className={`rounded-xl border p-4 ${item.is_accepted ? 'border-sev-low/25' : color}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold text-brand bg-brand-subtle px-1.5 py-0.5 rounded">{item.ref}</span>
            <EditableText value={item.description} onSave={(v) => onUpdate({ description: v })} multiline={false} className="font-medium text-fg"/>
            {item.is_accepted && <span className="text-xs text-sev-low font-medium flex items-center gap-1"><Check size={12}/> Accepted</span>}
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <span className="text-[10px] font-semibold uppercase text-fg-subtle">Process</span>
              <EditableText value={item.process} onSave={(v) => onUpdate({ process: v })} placeholder="Process / control objective"/>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-fg-subtle">Risk statement</span>
              <EditableText value={item.risk_statement} onSave={(v) => onUpdate({ risk_statement: v })} placeholder="Likelihood of X due to Y resulting in Z"/>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-fg-subtle">Controls in place</span>
              <EditableText value={item.controls} onSave={(v) => onUpdate({ controls: v })} placeholder="Key controls"/>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-fg-subtle">Link to ANL scope area</span>
              <EditableText value={item.link_to_anl} onSave={(v) => onUpdate({ link_to_anl: v })} placeholder="Scope area from ANL" multiline={false}/>
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 min-w-[100px]">
          <div className="text-[10px] text-fg-subtle">Inherent risk</div>
          <select value={item.inherent_risk} onChange={(e) => onUpdate({ inherent_risk: e.target.value })}
            className="text-xs border border-line rounded px-1.5 py-0.5">
            {RISK_LEVELS.map(l => <option key={l}>{l}</option>)}
          </select>
          <div className="text-[10px] text-fg-subtle mt-1">Residual risk</div>
          <select value={item.residual_risk} onChange={(e) => onUpdate({ residual_risk: e.target.value })}
            className={`text-xs border border-line rounded px-1.5 py-0.5 font-semibold ${residualColor}`}>
            {RISK_LEVELS.map(l => <option key={l}>{l}</option>)}
          </select>
          {!item.is_accepted && (
            <button onClick={onAccept} className="mt-2 flex items-center gap-1 rounded bg-sev-low/100 px-2 py-1 text-xs text-white hover:bg-sev-low/100">
              <Check size={11}/> Accept
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function BRAPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['bra', id] })
    qc.invalidateQueries({ queryKey: ['engagement', id] })
  }

  const { data: bra } = useQuery({
    queryKey: ['bra', id],
    queryFn: () => getBRA(id),
    refetchInterval: (q) => (q.state.data?.status === 'drafting' ? 3000 : false),
  })

  const draft = useMutation({ mutationFn: () => draftBRA(id), onSuccess: () => { showToast('Drafting background risk assessment…'); invalidate() } })
  const patch = useMutation({ mutationFn: (p) => updateBRA(id, p), onSuccess: invalidate })
  const updateItem = useMutation({ mutationFn: ({ ref, p }) => updateRiskItem(id, ref, p), onSuccess: invalidate })

  const downloadXlsx = async () => {
    try {
      await downloadFile(`/planning/${id}/bra/export-xlsx`, 'BRA-risk-assessment.xlsx')
    } catch {
      showToast('Export failed', 'error')
    }
  }

  const status = bra?.status || 'not_started'
  const riskItems = bra?.risk_items || []
  const acceptedCount = riskItems.filter(i => i.is_accepted).length

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-8">
      <button onClick={() => navigate(`/engagements/${id}/planning`)} className="mb-4 flex items-center gap-1 text-sm text-fg-muted hover:text-brand">
        <ArrowLeft size={16}/> Back to planning
      </button>

      <div className="flex items-center justify-between">
        <h1 className="text-h1 text-fg">Background Risk Assessment</h1>
        <div className="flex gap-2">
          <Button onClick={() => draft.mutate()} disabled={draft.isPending} variant={status === 'draft_ready' ? 'secondary' : 'primary'}>
            <Sparkles size={14}/> {status === 'draft_ready' ? 'Re-draft' : 'Draft with AI'}
          </Button>
          {status === 'draft_ready' && (
            <Button variant="ghost" onClick={downloadXlsx}><Download size={14}/> Download Excel</Button>
          )}
        </div>
      </div>
      <p className="mt-1 text-sm text-fg-muted">
        Four mandatory background sections + risk-per-scope-area table following the standard template. Export to Excel.
      </p>

      {status === 'drafting' && (
        <div className="border border-line mt-6 flex items-center gap-3 rounded-xl bg-surface p-5 text-sm text-fg-muted">
          <Loader2 size={20} className="animate-spin text-brand"/> Generating background sections and risk items from your planning data…
        </div>
      )}

      {status === 'not_started' && (
        <div className="border border-line mt-6 rounded-xl bg-surface p-6 text-center">
          <BarChart2 size={28} className="mx-auto text-brand-light mb-2"/>
          <p className="text-sm text-fg-muted">Click "Draft with AI" to generate the background sections and a risk assessment table based on your accepted Topic Intelligence memo and scope.</p>
        </div>
      )}

      {status === 'draft_ready' && (
        <>
          {/* Background sections */}
          <section className="mt-6">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-fg-subtle">Background information</h2>
            <div className="space-y-3">
              {BG_SECTIONS.map(({ key, label, hint }) => (
                <div key={key} className="border border-line rounded-xl bg-surface p-4">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-sm font-semibold text-fg">{label}</span>
                    <span className="text-xs text-fg-subtle">{hint}</span>
                  </div>
                  <EditableText value={bra[key] || ''} onSave={(v) => patch.mutate({ [key]: v })} placeholder="Click to edit…"/>
                </div>
              ))}
            </div>
          </section>

          {/* Risk items */}
          <section className="mt-8">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-fg-subtle">
                Risk assessment ({acceptedCount}/{riskItems.length} accepted)
              </h2>
            </div>
            <div className="space-y-3">
              {riskItems.map((item) => (
                <RiskRow
                  key={item.ref}
                  item={item}
                  onAccept={() => {
                    const updated = riskItems.map(i => i.ref === item.ref ? { ...i, is_accepted: true } : i)
                    patch.mutate({ risk_items: updated })
                  }}
                  onUpdate={(changes) => {
                    const updated = riskItems.map(i => i.ref === item.ref ? { ...i, ...changes } : i)
                    patch.mutate({ risk_items: updated })
                  }}
                />
              ))}
            </div>
          </section>

          <ScopeContributionPanel
            engagementId={id}
            generateFn={() => braGenerateScope(id)}
            getStoredFn={() => braGetScope(id)}
            publishFn={(payload) => braPublishScope(id, payload)}
            queryKey="bra-scope"
          />
        </>
      )}
    </div>
  )
}
