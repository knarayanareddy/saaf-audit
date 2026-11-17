import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ShieldCheck, Loader2, RefreshCw, Download, Lock, Check, AlertTriangle, ShieldAlert,
} from 'lucide-react'
import { getPrivacyGuard, runPrivacyGuard, downloadPrivacyAuditTrail } from '../../api/racm'
import { Card } from '../ui/Card'
import { useStore } from '../../store/useStore'
import Tooltip from '../ui/Tooltip'

// Privacy Guard — deterministic GDPR data-minimisation over the fieldwork
// dataset. Detects PII, classifies each field Required/Optional/Excessive per
// audit purpose, maps a GDPR legal basis, and masks/pseudonymises per role,
// with a tamper-evident audit trail. Free, no AI. It writes nothing into the
// matrix — it produces a masked view + a verifiable trail.

const PURPOSES = [
  'customer_due_diligence',
  'compliance_check',
  'breach_investigation',
  'reimbursement_review',
  'data_access_request',
]

const CLASS_STYLE = {
  required: 'bg-brand-subtle text-brand',
  optional: 'bg-surface-3 text-fg-muted',
  excessive: 'bg-sev-med/10 text-sev-med',
}

const title = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export default function PrivacyGuardPanel({ engagementId }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [role, setRole] = useState('auditor')
  const [purpose, setPurpose] = useState('customer_due_diligence')
  const [justification, setJustification] = useState('')

  const { data } = useQuery({
    queryKey: ['privacy-guard', engagementId],
    queryFn: () => getPrivacyGuard(engagementId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'pending' || s === 'running' ? 2000 : false
    },
  })

  const run = useMutation({
    mutationFn: () => runPrivacyGuard(engagementId, { role, purpose, justification }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['privacy-guard', engagementId] })
      showToast('Privacy scan started')
    },
  })

  const status = data?.status
  const result = data?.result
  const busy = status === 'pending' || status === 'running' || run.isPending
  const adminNeedsReason = role === 'admin' && justification.trim().length < 10

  // Aggregate the per-record field report to one row per field type: the
  // classification/category/legal basis are constant per field, so show a
  // representative masked example plus how many records carried it.
  const fieldRows = useMemo(() => {
    const report = result?.field_report || []
    const byField = new Map()
    for (const f of report) {
      const key = f.field_name
      if (!byField.has(key)) byField.set(key, { ...f, count: 0 })
      byField.get(key).count += 1
    }
    return [...byField.values()]
  }, [result])

  const configError = result && result.config_ok === false
  const summary = result?.summary

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
          <ShieldCheck size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Privacy Guard · GDPR data-minimisation</h3>
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            Detects personal data in the dataset, classifies each field Required / Optional / Excessive for
            the audit purpose, maps its GDPR legal basis, and masks or pseudonymises it for your role — with a
            tamper-evident audit trail. No AI; nothing is written into the matrix.
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="text-caption text-fg-subtle">Role</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="mt-1 w-full rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg"
          >
            <option value="auditor">Auditor — full masking (Required pseudonymised)</option>
            <option value="dpo">DPO — partial masking</option>
            <option value="admin">Admin — raw access (justification logged)</option>
          </select>
        </label>
        <label className="block">
          <span className="text-caption text-fg-subtle">Audit purpose</span>
          <select
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            className="mt-1 w-full rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg"
          >
            {PURPOSES.map((p) => <option key={p} value={p}>{title(p)}</option>)}
          </select>
        </label>
      </div>

      {role === 'admin' && (
        <div className="mt-3 rounded-lg bg-sev-med/10 p-3">
          <div className="flex items-center gap-1.5 text-caption font-medium text-sev-med">
            <ShieldAlert size={13} /> This role receives unmasked personal data.
          </div>
          <textarea
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Justification (required, recorded in the audit trail against every record) — e.g. Investigating ticket INC-4417."
            rows={2}
            className="mt-2 w-full rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-sm text-fg placeholder:text-fg-subtle"
          />
        </div>
      )}

      <div className="mt-3">
        <button
          onClick={() => run.mutate()}
          disabled={busy || adminNeedsReason}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : result && !configError ? <RefreshCw size={15} /> : <ShieldCheck size={15} />}
          {busy ? 'Scanning…' : result && !configError ? 'Re-run scan' : 'Run privacy scan'}
        </button>
        {adminNeedsReason && (
          <span className="ml-3 text-caption text-fg-subtle">Enter a justification (≥10 chars) to run as Admin.</span>
        )}
      </div>

      {status === 'failed' && (
        <div className="mt-4 rounded-lg bg-sev-high/10 px-3 py-2 text-sm text-sev-high">
          The scan did not complete. You can run it again.
        </div>
      )}

      {configError && (
        <div className="mt-4 rounded-lg bg-sev-med/10 px-3 py-2 text-sm text-sev-med">
          {result.message}
        </div>
      )}

      {result && !configError && status === 'complete' && summary && (
        <div className="mt-4 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-fg-subtle">
            <span>{summary.records_processed} records</span>
            <span>{summary.total_pii_fields} PII fields detected</span>
            <span>{summary.total_masked} masked / pseudonymised</span>
            <span className="font-medium text-brand">masking level: {String(summary.masking_level).toUpperCase()}</span>
          </div>

          {/* Field-level classification */}
          <div className="mt-3 space-y-2">
            {fieldRows.map((f) => (
              <div key={f.field_name} className="flex items-start gap-2 rounded-lg bg-surface-2 px-3 py-2">
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${CLASS_STYLE[f.classification] || 'bg-surface-3 text-fg-muted'}`}>
                  {f.classification}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 text-sm text-fg">
                    <span className="font-medium">{f.field_name}</span>
                    <span className="text-caption text-fg-subtle">{f.category}</span>
                    {f.legal_basis?.article && (
                      <Tooltip width="16rem" label={`The legal basis this finding rests on${f.legal_basis.title ? `: ${f.legal_basis.title}` : ''}. Check the article before relying on it.`}>
                        <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[11px] text-fg-muted">
                          {f.legal_basis.article}{f.legal_basis.title ? ` · ${f.legal_basis.title}` : ''}
                        </span>
                      </Tooltip>
                    )}
                  </div>
                  <div className="mt-0.5 font-mono text-caption text-fg-muted">
                    e.g. {f.masked_value}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Audit trail */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-2 px-3 py-2">
            <span className={`inline-flex items-center gap-1.5 text-caption font-medium ${result.chain_intact ? 'text-sev-low' : 'text-sev-high'}`}>
              {result.chain_intact ? <Check size={13} /> : <AlertTriangle size={13} />}
              {result.chain_intact
                ? `Audit trail hash-chain intact — ${(result.audit_trail || []).length} entries`
                : 'Audit trail broken — tampered'}
            </span>
            <button
              onClick={() => downloadPrivacyAuditTrail(engagementId)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-brand/30 px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-brand-faint"
            >
              <Download size={14} /> Download audit log (JSONL)
            </button>
          </div>

          {summary.masking_level !== 'none' && (
            <p className="mt-2 inline-flex items-center gap-1 text-caption text-fg-subtle">
              <Lock size={11} /> Original values never leave the system for this role.
            </p>
          )}
        </div>
      )}
    </Card>
  )
}
